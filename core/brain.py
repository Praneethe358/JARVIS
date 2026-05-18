"""
core/brain.py
─────────────
Reasoning core for NEXUS.

Primary path  : OpenRouter API (https://openrouter.ai/api/v1/chat/completions)
                Default model : deepseek/deepseek-r1:free
                Fallback model: meta-llama/llama-4-scout:free
                Auth          : Bearer token via OPENROUTER_API_KEY in .env

Conversation history : last 6 messages (3 exchanges) kept in-memory.
System prompt        : injected as a system role message into every call.
Response sanitizer   : strips markdown before passing text to TTS engine.

Migration note: Previously used Ollama (http://127.0.0.1:11434/api/generate).
                Fully replaced with OpenRouter's OpenAI-compatible v1 endpoint.
"""

import re
import json
import time
import urllib.request
import urllib.error
from collections import deque
from core.logger import log

# ── NEXUS system prompt ────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are NEXUS, a Linux-native AI automation framework and personal assistant. "
    "Respond concisely and conversationally — your replies will be spoken aloud via "
    "TTS so avoid markdown, bullet points, symbols, or long paragraphs. "
    "Keep answers under 3 sentences unless detail is explicitly requested. "
    "Be sharp, intelligent, and direct."
)

# ── OpenRouter endpoint ────────────────────────────────────────────────────────
_OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_REFERER = "https://your-nexus-app.com"
_OPENROUTER_TITLE   = "Nexus Dashboard"

# ── Response cache (keyed by prompt hash) ─────────────────────────────────────
_response_cache: dict = {}   # { hash: {"response": str, "ts": float} }
_CACHE_TTL = 300             # 5 minutes


def sanitize_for_tts(text: str) -> str:
    """
    Strip all markdown symbols before text reaches the TTS engine.
    Removes: **, *, #, `, -, ~, > and collapses whitespace.
    Also handles <think>...</think> blocks that DeepSeek-R1 emits.
    """
    # Strip DeepSeek <think> reasoning blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"\*+", "", text)           # bold/italic
    text = re.sub(r"#+\s*", "", text)         # headings
    text = re.sub(r"`+", "", text)            # code
    text = re.sub(r"(?m)^[\-~>\s]*[\-~>]\s+", "", text)  # bullet lines
    text = re.sub(r"\n{2,}", " ", text)       # multiple blank lines
    text = text.replace("\n", " ")            # remaining newlines
    text = re.sub(r" {2,}", " ", text)        # duplicate spaces
    return text.strip()


def _cache_get(key: str) -> str | None:
    """Return cached response if still within TTL, else None."""
    entry = _response_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["response"]
    return None


def _cache_set(key: str, response: str):
    """Store response in cache with current timestamp."""
    _response_cache[key] = {"response": response, "ts": time.time()}


class Brain:
    """Reasoning core — OpenRouter primary, local keyword fallback."""

    def __init__(self):
        # Short-term conversation history: last 6 messages (3 exchanges)
        self.history: deque = deque(maxlen=6)
        # Active OpenRouter model — read from config
        from core.config import CONFIG
        self._model: str = CONFIG.get("openrouter_model", "deepseek/deepseek-r1:free")
        self._fallback_model: str = CONFIG.get(
            "openrouter_fallback_model", "meta-llama/llama-4-scout:free"
        )
        self._api_key: str = CONFIG.get("openrouter_api_key", "")
        # Flag set on boot by the OpenRouter health check in main.py
        self.openrouter_available: bool = True
        log.info(f"Brain initialised — model: {self._model}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def think(self, user_input: str, context: str = "") -> str:
        """
        Main reasoning entry point called by the router.
        If a skill provided context, return it directly.
        Otherwise, call OpenRouter with full conversation history.
        """
        # Skill produced a concrete result — pass it through unchanged
        if context:
            self.history.append({"role": "user",      "content": user_input})
            self.history.append({"role": "assistant",  "content": context})
            return context

        # Try OpenRouter reasoning
        if self.openrouter_available:
            response = self._openrouter_query(user_input)
            if response:
                clean = sanitize_for_tts(response)
                self.history.append({"role": "user",      "content": user_input})
                self.history.append({"role": "assistant",  "content": clean})
                return clean

        # Graceful fallback: local keyword replies
        log.warning("OpenRouter unavailable — using local keyword fallback.")
        reply = self._local_reply(user_input)
        self.history.append({"role": "user",      "content": user_input})
        self.history.append({"role": "assistant",  "content": reply})
        return reply

    def ask_ai(self, prompt: str, system_prompt: str = None, use_cache: bool = True) -> str:
        """
        Direct OpenRouter call — used by skills (StudySkill, StockAnalyst, etc.)
        that want a raw LLM response without touching conversation history.

        Args:
            prompt       : The user/task prompt to send.
            system_prompt: Optional custom system prompt (overrides default).
            use_cache    : If True, cache the response for 5 minutes.

        Returns sanitized text, or empty string on failure.
        """
        if not self.openrouter_available:
            return ""

        # Cache lookup
        if use_cache:
            cache_key = str(hash((system_prompt or _SYSTEM_PROMPT, prompt)))
            cached = _cache_get(cache_key)
            if cached:
                log.info("Brain.ask_ai: returning cached response")
                return cached

        result = self._openrouter_query(
            prompt,
            system_override=system_prompt,
            include_history=False   # direct calls are stateless
        )
        clean = sanitize_for_tts(result) if result else ""

        if clean and use_cache:
            _cache_set(cache_key, clean)

        return clean

    # Backwards-compatible alias (StudySkill used ask_ollama before migration)
    def ask_ollama(self, prompt: str) -> str:
        """Legacy alias → ask_ai(). Kept so old skill code doesn't break."""
        return self.ask_ai(prompt)

    def switch_model(self, model_name: str):
        """
        Update the active OpenRouter model at runtime and persist to config.json.
        Called by the router when the user says 'switch model to [name]'.
        """
        self._model = model_name
        log.info(f"OpenRouter model switched to: {model_name}")

        # Persist the new model name to config.json so it survives restarts
        try:
            with open("config.json", "r") as f:
                cfg = json.load(f)
            cfg["openrouter_model"] = model_name
            with open("config.json", "w") as f:
                json.dump(cfg, f, indent=2)
            log.info("openrouter_model persisted to config.json")
        except Exception as e:
            log.warning(f"Could not persist model to config.json: {e}")

    def clear_memory(self):
        """Wipe short-term conversation history."""
        self.history.clear()
        log.info("Conversation memory cleared.")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _openrouter_query(
        self,
        user_input: str,
        system_override: str = None,
        include_history: bool = True,
    ) -> str:
        """
        POST to OpenRouter /v1/chat/completions using urllib.request.

        Why urllib: consistent with the rest of the codebase and avoids any
        proxy interference that affected the old Ollama integration.

        OpenRouter uses the OpenAI-compatible messages array format:
          [{"role": "system", ...}, {"role": "user", ...}, ...]
        """
        if not self._api_key:
            log.error("OPENROUTER_API_KEY is not set. Check your .env file.")
            self.openrouter_available = False
            return ""

        system_msg = system_override or _SYSTEM_PROMPT

        # ── Build messages array ─────────────────────────────────────────────
        messages = [{"role": "system", "content": system_msg}]

        if include_history:
            for msg in self.history:     # last 6 messages (3 exchanges)
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_input})

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
        }).encode("utf-8")

        # ── POST via urllib ──────────────────────────────────────────────────
        try:
            req = urllib.request.Request(
                _OPENROUTER_URL,
                data=payload,
                headers={
                    "Authorization"  : f"Bearer {self._api_key}",
                    "Content-Type"   : "application/json",
                    "HTTP-Referer"   : _OPENROUTER_REFERER,
                    "X-Title"        : _OPENROUTER_TITLE,
                },
                method="POST",
            )
            # Timeout: 30s — OpenRouter is cloud-based, fast
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # OpenAI-compatible response format
                choices = data.get("choices", [])
                if not choices:
                    log.warning(f"OpenRouter returned empty choices: {data}")
                    return ""
                return choices[0].get("message", {}).get("content", "").strip()

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            log.error(f"OpenRouter HTTP error: {e.code} {e.reason} — {body[:200]}")
            # 429 = rate limit, 402 = quota — don't disable permanently
            if e.code not in (429, 402):
                self.openrouter_available = False
            return ""
        except urllib.error.URLError as e:
            log.error(f"OpenRouter connection error: {e.reason}")
            self.openrouter_available = False
            return ""
        except TimeoutError:
            log.warning("OpenRouter request timed out — will retry on next command.")
            return ""
        except Exception as e:
            log.error(f"OpenRouter query failed: {e}")
            return ""

    def _local_reply(self, user_input: str) -> str:
        """
        Minimal keyword-based fallback — only used when OpenRouter is offline.
        """
        text = user_input.lower().strip()

        if any(p in text for p in ["how are you", "how r you", "how r u"]):
            return "I am running on base systems, Sir. Reasoning core is offline."

        if any(p in text for p in ["who are you", "what are you"]):
            return "I am NEXUS, your local assistant. Reasoning core is currently offline."

        if any(p in text for p in ["what can you do", "help", "features"]):
            return (
                "I can open apps, handle notes and reminders, manage your schedule, "
                "check weather or news, and control system functions. "
                "My reasoning core is offline, so open-ended questions are limited."
            )

        if any(p in text for p in ["thank you", "thanks"]):
            return "You are welcome, Sir."

        if any(p in text for p in ["good night", "bye", "goodbye"]):
            return "Goodbye, Sir."

        return "My reasoning core is offline. Running on base systems only."
