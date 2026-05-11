"""
core/config.py  +  core/logger.py  (combined for convenience)
──────────────────────────────────────────────────────────────
"""

# ── config.py ────────────────────────────────────────────────────────────────

import json, os

try:
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(dotenv_path)
except Exception:
    pass

_DEFAULT_CONFIG = {
    "openweather_api_key"  : os.getenv("OPENWEATHER_API_KEY", ""),
    "newsapi_key"          : os.getenv("NEWSAPI_KEY", ""),
    "spotify_client_id"    : os.getenv("SPOTIFY_CLIENT_ID", ""),
    "spotify_client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    "porcupine_access_key" : os.getenv("PORCUPINE_ACCESS_KEY", ""),
    "mic_device_index"     : None,         # Set to integer index if default mic fails
    "city"                 : "Coimbatore",
    "user_name"            : "Praneeth",
    "stt_backend"          : "google",     # "google" | "whisper"
    "wake_backend"         : "sr",         # "sr"     | "porcupine"
    "tts_rate"             : 175,
    "tts_volume"           : 0.9,
    "face_auth_enabled"    : False,
    "news_country"         : "in",
    "news_category"        : "technology",
}

_ENV_OVERRIDES = {
    "openweather_api_key": "OPENWEATHER_API_KEY",
    "newsapi_key": "NEWSAPI_KEY",
    "spotify_client_id": "SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "SPOTIFY_CLIENT_SECRET",
}

def _load_config() -> dict:
    path = "config.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            user_cfg = json.load(f)
        merged = {**_DEFAULT_CONFIG, **user_cfg}
    else:
        merged = _DEFAULT_CONFIG.copy()
        # Write default config so user can edit it easily
        with open(path, "w") as f:
            json.dump(merged, f, indent=2)

    for config_key, env_key in _ENV_OVERRIDES.items():
        env_value = os.getenv(env_key)
        if env_value:
            merged[config_key] = env_value
    return merged

CONFIG = _load_config()


# ── logger.py ────────────────────────────────────────────────────────────────

import logging
import os

os.makedirs("data", exist_ok=True)

# File handler — full verbose log
_file_handler = logging.FileHandler("data/nexus.log", mode="a")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
))

# Console handler — WARN and above only (critical runtime alerts)
import core.ui as _ui

class _UIHandler(logging.Handler):
    """Routes WARN/ERROR log records through the styled ui.status() lines."""
    def emit(self, record):
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            _ui.status(msg, "err")
        elif record.levelno >= logging.WARNING:
            _ui.status(msg, "warn")

_console_handler = _UIHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter("%(message)s"))

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[_file_handler, _console_handler],
)
log = logging.getLogger("NEXUS")
