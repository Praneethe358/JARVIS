"""
core/brain.py
─────────────
Reasoning core for NEXUS.

Primary path  : Ollama (http://127.0.0.1:11434/api/generate) — mistral model
                Uses 127.0.0.1 explicitly; 'localhost' resolves to IPv6 on
                this system but Ollama only binds to IPv4.
Fallback path : Local keyword replies when Ollama is unreachable.

Conversation history : last 6 messages (3 exchanges) kept in-memory.
System prompt        : injected into every Ollama call for consistent persona.
Response sanitizer   : strips markdown before passing text to TTS engine.
"""

import re
import json
import urllib.request
import urllib.error
from collections import deque
from core.logger import log

# ── NEXUS system prompt ────────────────────────────────────────────────────────
# Injected at the top of every Ollama prompt to enforce persona & TTS-safe style.
_SYSTEM_PROMPT = (
    "You are NEXUS, a Linux-native AI automation framework and personal assistant. "
    "Respond concisely and conversationally — your replies will be spoken aloud via "
    "TTS so avoid markdown, bullet points, symbols, or long paragraphs. "
    "Keep answers under 3 sentences unless detail is explicitly requested. "
    "Be sharp, intelligent, and direct."
)

# ── Ollama endpoints ───────────────────────────────────────────────────────────
# IMPORTANT: Use 127.0.0.1, NOT 'localhost'.
# On this system, 'localhost' resolves to IPv6 (::1) but Ollama only binds
# to IPv4 (127.0.0.1:11434), causing spurious "Not Found" / URLError failures.
_OLLAMA_GENERATE = "http://127.0.0.1:11434/api/generate"


def sanitize_for_tts(text: str) -> str:
    """
    Strip all markdown symbols before text reaches the TTS engine.
    Removes: **, *, #, `, -, ~, > and collapses whitespace.
    """
    text = re.sub(r"\*+", "", text)           # bold/italic
    text = re.sub(r"#+\s*", "", text)         # headings
    text = re.sub(r"`+", "", text)            # code
    text = re.sub(r"(?m)^[\-~>\s]*[\-~>]\s+", "", text)  # bullet lines
    text = re.sub(r"\n{2,}", " ", text)       # multiple blank lines
    text = text.replace("\n", " ")            # remaining newlines
    text = re.sub(r" {2,}", " ", text)        # duplicate spaces
    return text.strip()


class Brain:
    """Reasoning core — Ollama primary, local keyword fallback."""

    def __init__(self):
        # Short-term conversation history: last 6 messages (3 exchanges)
        self.history: deque = deque(maxlen=6)
        # Active Ollama model — read from config, default to mistral
        from core.config import CONFIG
        self._model: str = CONFIG.get("ollama_model", "mistral")
        # Flag set on boot by the Ollama health check in main.py
        self.ollama_available: bool = True
        log.info(f"Brain initialised — model: {self._model}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def think(self, user_input: str, context: str = "") -> str:
        """
        Main reasoning entry point called by the router.
        If a skill provided context, return it directly.
        Otherwise, call Ollama with full conversation history.
        """
        # Skill produced a concrete result — pass it through unchanged
        if context:
            self.history.append({"role": "user",      "content": user_input})
            self.history.append({"role": "assistant",  "content": context})
            return context

        # Try Ollama reasoning
        if self.ollama_available:
            response = self._ollama_query(user_input)
            if response:
                clean = sanitize_for_tts(response)
                self.history.append({"role": "user",      "content": user_input})
                self.history.append({"role": "assistant",  "content": clean})
                return clean

        # Graceful fallback: local keyword replies
        log.warning("Ollama unavailable — using local keyword fallback.")
        reply = self._local_reply(user_input)
        self.history.append({"role": "user",      "content": user_input})
        self.history.append({"role": "assistant",  "content": reply})
        return reply

    def ask_ollama(self, prompt: str) -> str:
        """
        Direct Ollama call — used by StudySkill and others that want a raw
        LLM response without touching conversation history.
        Returns sanitized text, or empty string on failure.
        """
        if not self.ollama_available:
            return ""
        result = self._ollama_query(prompt)
        return sanitize_for_tts(result) if result else ""

    def switch_model(self, model_name: str):
        """
        Update the active Ollama model at runtime and persist to config.json.
        Called by the router when the user says 'switch model to [name]'.
        """
        self._model = model_name
        log.info(f"Ollama model switched to: {model_name}")

        # Persist the new model name to config.json so it survives restarts
        try:
            with open("config.json", "r") as f:
                cfg = json.load(f)
            cfg["ollama_model"] = model_name
            with open("config.json", "w") as f:
                json.dump(cfg, f, indent=2)
            log.info("ollama_model persisted to config.json")
        except Exception as e:
            log.warning(f"Could not persist model to config.json: {e}")

    def clear_memory(self):
        """Wipe short-term conversation history."""
        self.history.clear()
        log.info("Conversation memory cleared.")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _ollama_query(self, user_input: str) -> str:
        """
        POST to Ollama /api/generate using urllib.request (NOT requests lib).

        Why urllib: the 'requests' library silently routes 127.0.0.1 traffic
        through a system proxy on this machine, returning 404. urllib hits the
        TCP socket directly, bypassing any proxy layer.

        Conversation history + system prompt are serialised into a single
        formatted prompt string so context carries across turns.
        """
        # ── Build prompt: system + rolling history + current message ─────────
        prompt_parts = [f"[SYSTEM] {_SYSTEM_PROMPT}\n"]
        for msg in self.history:   # last 6 messages (3 exchanges)
            role = "User" if msg["role"] == "user" else "NEXUS"
            prompt_parts.append(f"{role}: {msg['content']}")
        prompt_parts.append(f"User: {user_input}")
        prompt_parts.append("NEXUS:")   # instruct the model to continue here
        full_prompt = "\n".join(prompt_parts)

        payload = json.dumps(
            {"model": self._model, "prompt": full_prompt, "stream": False}
        ).encode("utf-8")

        # ── POST via urllib — direct socket, no proxy ────────────────────────
        try:
            req = urllib.request.Request(
                _OLLAMA_GENERATE,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # Timeout: 120s — Mistral on CPU can take 60-90s for long queries
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()

        except urllib.error.HTTPError as e:
            # Server responded with an HTTP error code (4xx/5xx)
            log.error(f"Ollama HTTP error: {e.code} {e.reason}")
            return ""
        except urllib.error.URLError as e:
            # Connection refused / DNS failure — Ollama is genuinely down
            log.error(f"Ollama connection error: {e.reason}")
            self.ollama_available = False   # disable until next boot
            return ""
        except TimeoutError:
            # Transient slowness — do NOT disable Ollama, just skip this request
            log.warning("Ollama request timed out — will retry on next command.")
            return ""
        except Exception as e:
            log.error(f"Ollama query failed: {e}")
            return ""

    def _local_reply(self, user_input: str) -> str:
        """
        Minimal keyword-based fallback — only used when Ollama is offline.
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
