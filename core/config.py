"""
core/config.py  +  core/logger.py  (combined for convenience)
──────────────────────────────────────────────────────────────
"""

# ── config.py ────────────────────────────────────────────────────────────────

import json, os

_DEFAULT_CONFIG = {
    "openai_api_key"       : os.getenv("OPENAI_API_KEY", ""),
    "openweather_api_key"  : os.getenv("OPENWEATHER_API_KEY", ""),
    "newsapi_key"          : os.getenv("NEWSAPI_KEY", ""),
    "spotify_client_id"    : os.getenv("SPOTIFY_CLIENT_ID", ""),
    "spotify_client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    "city"                 : "Coimbatore",
    "user_name"            : "Praneeth",
    "stt_backend"          : "google",     # "google" | "whisper"
    "wake_backend"         : "sr",          # "sr"     | "porcupine"
    "tts_rate"             : 175,
    "tts_volume"           : 0.9,
    "face_auth_enabled"    : False,
    "news_country"         : "in",
    "news_category"        : "technology",
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
    return merged

CONFIG = _load_config()


# ── logger.py ────────────────────────────────────────────────────────────────

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/jarvis.log", mode="a")
    ]
)
log = logging.getLogger("JARVIS")
