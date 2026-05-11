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

_ENV_OVERRIDES = {
    "openai_api_key": "OPENAI_API_KEY",
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
