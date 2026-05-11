"""
core/brain.py
─────────────
Reasoning core for NEXUS.

Primary path  : Ollama (http://localhost:11434) — mistral model
Fallback path : Local keyword replies when Ollama is unreachable

Conversation history:  last 6 messages (3 exchanges) kept in-memory.
System prompt:         injected into every Ollama call for consistent persona.
Response sanitizer:    strips markdown before passing text to TTS engine.
"""

import re
import json
import requests
from collections import deque
from core.logger import log

# ── NEXUS system prompt ────────────────────────────────────────────────────────
# Injected as the first message in every Ollama request to enforce persona.
_SYSTEM_PROMPT = (
    "You are NEXUS, a Linux-native AI automation framework and personal assistant. "
    "Respond concisely and conversationally — your replies will be spoken aloud via "
    "TTS so avoid markdown, bullet points, symbols, or long paragraphs. "
    "Keep answers under 3 sentences unless detail is explicitly requested. "
    "Be sharp, intelligent, and direct."
)

# ── Ollama API endpoint ────────────────────────────────────────────────────────
_OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"


def sanitize_for_tts(text: str) -> str:
    """
    Strip all markdown symbols before text reaches the TTS engine.
    Removes: **, *, #, `, -, ~, > and excess whitespace.
    """
    # Remove bold/italic markers
    text = re.sub(r"\*+", "", text)
    # Remove headings
    text = re.sub(r"#+\s*", "", text)
    # Remove inline code and code blocks
    text = re.sub(r"`+", "", text)
    # Remove leading bullet/dash/tilde characters on lines
    text = re.sub(r"(?m)^[\-~>\s]*[\-~>]\s+", "", text)
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{2,}", " ", text)
    # Replace remaining newlines with a space
    text = text.replace("\n", " ")
    # Collapse duplicate spaces
    text = re.sub(r" {2,}", " ", text)
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
        If a skill provided context, inject it and skip Ollama.
        Otherwise, call Ollama with full conversation history.
        """
        # If a skill already produced a concrete result, return it directly.
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
        Direct Ollama call — used by StudySkill and other skills that
        want raw LLM responses bypassing the local keyword fallback.
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
        import json as _json
        self._model = model_name
        log.info(f"Ollama model switched to: {model_name}")

        # Persist the new model name to config.json
        try:
            with open("config.json", "r") as f:
                cfg = _json.load(f)
            cfg["ollama_model"] = model_name
            with open("config.json", "w") as f:
                _json.dump(cfg, f, indent=2)
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
        POST to Ollama /api/chat.
        Prepends the NEXUS system prompt and appends the full conversation
        history so the model has context across turns.
        Returns the assistant's reply string, or empty string on error.
        """
        # Build message list: system prompt + conversation history + new user message
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.extend(list(self.history))           # last 6 messages
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,                          # single response, not streaming
        }

        try:
            resp = requests.post(
                _OLLAMA_ENDPOINT,
                json=payload,
                timeout=30,                           # allow up to 30s for inference
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()

        except requests.exceptions.ConnectionError:
            log.error("Ollama unreachable (ConnectionError).")
            self.ollama_available = False
            return ""
        except requests.exceptions.Timeout:
            log.error("Ollama request timed out.")
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

        # Final fallback — let the user know Ollama is down
        return "My reasoning core is offline. Running on base systems only."
