"""
config.py
─────────
Configuration for NEXUS Voice Assistant Pipeline.
Loads environment variables from .env and defines static settings.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ── API KEYS ────────────────────────────────────────────────────────
NVIDIA_API_KEY        = os.getenv("NVIDIA_API_KEY", "")
OPENROUTER_API_KEY    = os.getenv("OPENROUTER_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY       = os.getenv("FINNHUB_API_KEY", "")

# ── LLM SETTINGS (OpenRouter) ───────────────────────────────────────
OPENROUTER_URL        = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL_DEFAULT     = "openrouter/free"
LLM_MODEL_FALLBACK    = "meta-llama/llama-4-scout:free"
LLM_SYSTEM_PROMPT     = (
    "You are NEXUS, an advanced AI voice assistant with financial "
    "intelligence and general knowledge. You can answer anything — "
    "stocks, gold, crypto, news, science, casual conversation, or "
    "personal queries. Be concise and sharp. For voice output, "
    "keep responses under 3 sentences unless the user asks for detail. "
    "Never say you cannot answer a general question — reason through it. "
    "If the user asks you to open, show, find, or search for something online, "
    "respond ONLY with: [BROWSER:https://full-url-here]"
)
LLM_HEADERS           = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://nexus-assistant.local",
    "X-Title": "NEXUS"
}

# ── STT SETTINGS (NVIDIA Parakeet) ──────────────────────────────────
NVIDIA_STT_URL        = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/d8dd4e9b-fbf5-4fb0-9dba-8cf436c8d965"
NVIDIA_STT_HEADERS    = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Accept": "application/json"
}

# ── AUDIO & TTS SETTINGS ────────────────────────────────────────────
SAMPLE_RATE           = 16000
CHANNELS              = 1
TTS_VOICE             = "en-US-GuyNeural"
TTS_RATE              = "+5%"
VAD_MODE              = 2   # 0-3 (higher is more aggressive silence detection)
SILENCE_TIMEOUT_SEC   = 1.5 # seconds of silence before cutting off recording
MAX_RECORD_SEC        = 10.0 # max record time in seconds

# ── CACHING ─────────────────────────────────────────────────────────
CACHE_TTL_SEC         = 300 # 5 minutes

