"""
skills/news.py      — Top headlines via NewsAPI
skills/calendar.py  — Google Calendar integration
skills/music.py     — Spotify playback control
skills/search.py    — DuckDuckGo web search
skills/system.py    — OS-level control (volume, apps, shutdown)

All in one file for convenience; split into separate files for production.

INSTALL:
    pip install newsapi-python requests spotipy pyautogui psutil
"""

# ══════════════════════════════════════════════════════════════════════════════
# NEWS SKILL
# ══════════════════════════════════════════════════════════════════════════════

import requests as _requests
from core.config import CONFIG
from core.logger import log


class NewsSkill:
    """Fetch top headlines from NewsAPI."""

    triggers = ["news", "headlines", "what's happening", "latest", "top stories"]

    def handle(self, command: str) -> str:
        api_key  = CONFIG.get("newsapi_key", "")
        category = CONFIG.get("news_category", "technology")
        country  = CONFIG.get("news_country", "in")

        if not api_key:
            return "[News] API key not set. Add newsapi_key to config.json. Get free key at newsapi.org"

        try:
            url  = "https://newsapi.org/v2/top-headlines"
            resp = _requests.get(url, params={
                "country"  : country,
                "category" : category,
                "pageSize" : 5,
                "apiKey"   : api_key,
            }, timeout=5)
            data = resp.json()

            if resp.status_code != 200:
                return f"[News] Error: {data.get('message')}"

            articles = data.get("articles", [])
            if not articles:
                return "[News] No headlines found."

            headlines = [f"{i+1}. {a['title']}" for i, a in enumerate(articles[:5])]
            result    = "Top headlines:\n" + "\n".join(headlines)
            log.info(f"[NewsSkill] Fetched {len(headlines)} headlines.")
            return result

        except Exception as e:
            log.error(f"NewsSkill error: {e}")
            return "[News] Unable to fetch news."


# ══════════════════════════════════════════════════════════════════════════════
# CALENDAR SKILL
# ══════════════════════════════════════════════════════════════════════════════

import datetime
import json
import os


class CalendarSkill:
    """
    Google Calendar integration via google-calendar-simple-api.

    INSTALL:
        pip install gcsa google-auth google-auth-oauthlib google-auth-httplib2

    SETUP (one-time):
        1. Go to console.cloud.google.com
        2. Create project → enable Google Calendar API
        3. Create OAuth credentials → download as credentials.json
        4. Place credentials.json in the jarvis/ folder
        5. First run: browser opens → authorise access
    """

    triggers = ["calendar", "schedule", "appointment", "meeting", "remind",
                "what's today", "agenda", "event", "add event"]

    LOCAL_EVENTS_FILE = "data/local_events.json"  # fallback if no Google auth

    def __init__(self):
        self._events = self._load_local()

    def handle(self, command: str) -> str:
        if any(w in command for w in ["add", "schedule", "create", "set reminder"]):
            return self._add_event(command)
        else:
            return self._list_events()

    def _list_events(self) -> str:
        today = datetime.date.today()
        upcoming = [
            e for e in self._events
            if datetime.date.fromisoformat(e["date"]) >= today
        ]
        upcoming.sort(key=lambda e: e["date"])

        if not upcoming:
            return "[Calendar] No upcoming events."

        lines = [f"• {e['date']} {e.get('time','')} — {e['title']}" for e in upcoming[:5]]
        return "Upcoming events:\n" + "\n".join(lines)

    def _add_event(self, command: str) -> str:
        """
        Simple parser for commands like:
        'add event team meeting on 2025-06-15 at 10:00'
        """
        import re
        date_m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', command)
        time_m = re.search(r'\bat\s+(\d{1,2}:\d{2})\b', command)

        date = date_m.group(1) if date_m else str(datetime.date.today())
        time = time_m.group(1) if time_m else ""

        # Extract event title (heuristic: after "event" keyword)
        title = command
        for kw in ["add event", "schedule", "create event", "set reminder for"]:
            if kw in title:
                title = title.split(kw, 1)[-1].strip()
                break
        # Strip date/time from title
        title = re.sub(r'\d{4}-\d{2}-\d{2}', '', title)
        title = re.sub(r'at \d{1,2}:\d{2}', '', title).strip(" ,.")

        event = {"title": title or "New event", "date": date, "time": time}
        self._events.append(event)
        self._save_local()
        return f"[Calendar] Added: '{event['title']}' on {date} {time}."

    def _load_local(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.LOCAL_EVENTS_FILE):
            with open(self.LOCAL_EVENTS_FILE, "r") as f:
                return json.load(f)
        return []

    def _save_local(self):
        with open(self.LOCAL_EVENTS_FILE, "w") as f:
            json.dump(self._events, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# MUSIC SKILL
# ══════════════════════════════════════════════════════════════════════════════


class MusicSkill:
    """
    Spotify playback control via spotipy.

    INSTALL:
        pip install spotipy

    SETUP:
        1. Go to developer.spotify.com → Create App
        2. Set Redirect URI to: http://localhost:8888/callback
        3. Add client_id, client_secret to config.json
        4. First run opens browser for Spotify auth
    """

    triggers = ["play", "music", "song", "pause", "next", "previous",
                "volume up", "volume down", "playlist", "spotify", "skip"]

    def __init__(self):
        self._sp = None  # lazy-init to avoid blocking startup

    def _get_sp(self):
        if self._sp:
            return self._sp
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            self._sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id     = CONFIG.get("spotify_client_id", ""),
                client_secret = CONFIG.get("spotify_client_secret", ""),
                redirect_uri  = "http://localhost:8888/callback",
                scope="user-modify-playback-state user-read-playback-state"
            ))
            return self._sp
        except ImportError:
            return None
        except Exception as e:
            log.error(f"Spotify init error: {e}")
            return None

    def handle(self, command: str) -> str:
        sp = self._get_sp()
        if not sp:
            return "[Music] Spotify not configured. Add credentials to config.json."

        try:
            if "pause" in command or "stop music" in command:
                sp.pause_playback()
                return "[Music] Playback paused."

            elif "next" in command or "skip" in command:
                sp.next_track()
                return "[Music] Skipped to next track."

            elif "previous" in command or "back" in command:
                sp.previous_track()
                return "[Music] Playing previous track."

            elif "resume" in command:
                sp.start_playback()
                return "[Music] Playback resumed."

            elif "play" in command:
                # Extract song/artist name
                import re
                song = re.sub(r'\b(play|music|song|on spotify)\b', '', command).strip()
                if song:
                    results = sp.search(q=song, limit=1, type="track")
                    tracks  = results["tracks"]["items"]
                    if tracks:
                        uri = tracks[0]["uri"]
                        sp.start_playback(uris=[uri])
                        name   = tracks[0]["name"]
                        artist = tracks[0]["artists"][0]["name"]
                        return f"[Music] Now playing: {name} by {artist}."
                    else:
                        return f"[Music] Could not find '{song}' on Spotify."
                else:
                    sp.start_playback()
                    return "[Music] Resuming playback."

            return "[Music] Command not understood."

        except Exception as e:
            log.error(f"MusicSkill error: {e}")
            return f"[Music] Error: {str(e)}"


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH SKILL
# ══════════════════════════════════════════════════════════════════════════════

import webbrowser


class SearchSkill:
    """DuckDuckGo web search — returns snippet, optionally opens browser."""

    triggers = ["search", "look up", "google", "find", "what is", "who is",
                "tell me about", "search for", "browse"]

    def handle(self, command: str) -> str:
        import re
        query = command
        for kw in ["search for", "search", "look up", "google", "find",
                   "tell me about", "what is", "who is"]:
            if kw in query:
                query = query.split(kw, 1)[-1].strip()
                break

        if not query:
            return "[Search] No query provided."

        # DuckDuckGo Instant Answer API (no key needed)
        try:
            url  = "https://api.duckduckgo.com/"
            resp = _requests.get(url, params={
                "q": query, "format": "json", "no_html": 1, "skip_disambig": 1
            }, timeout=5)
            data = resp.json()

            abstract = data.get("AbstractText", "")
            if abstract:
                snippet = abstract[:400] + ("..." if len(abstract) > 400 else "")
                result  = f"[Search] {snippet}"
            else:
                # Fall back: open browser
                webbrowser.open(f"https://www.google.com/search?q={query.replace(' ','+')}")
                result = f"[Search] No quick answer found. Opened browser for '{query}'."

            log.info(f"[SearchSkill] query='{query}'")
            return result

        except Exception as e:
            log.error(f"SearchSkill error: {e}")
            return "[Search] Search failed."


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM SKILL
# ══════════════════════════════════════════════════════════════════════════════

import os as _os
import subprocess
import platform


class SystemSkill:
    """OS-level controls: volume, open apps, shutdown, screenshots."""

    triggers = ["volume", "open", "launch", "shutdown", "restart", "screenshot",
                "battery", "cpu", "ram", "memory", "brightness"]

    def handle(self, command: str) -> str:
        system = platform.system().lower()

        if "screenshot" in command:
            return self._screenshot()

        elif "volume up" in command:
            return self._volume(+10, system)

        elif "volume down" in command:
            return self._volume(-10, system)

        elif "mute" in command:
            return self._mute(system)

        elif "shutdown" in command:
            return self._shutdown(system)

        elif "restart" in command:
            return self._restart(system)

        elif "open" in command or "launch" in command:
            return self._open_app(command)

        elif "battery" in command:
            return self._battery()

        elif any(w in command for w in ["cpu", "ram", "memory"]):
            return self._system_stats()

        return "[System] Command not recognised."

    def _screenshot(self) -> str:
        try:
            import pyautogui
            from datetime import datetime
            fname = f"data/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot(fname)
            return f"[System] Screenshot saved: {fname}"
        except Exception as e:
            return f"[System] Screenshot failed: {e}"

    def _volume(self, delta: int, system: str) -> str:
        try:
            if system == "windows":
                import pyautogui
                key = "volumeup" if delta > 0 else "volumedown"
                for _ in range(abs(delta) // 2):
                    pyautogui.press(key)
            elif system == "linux":
                cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {'+' if delta>0 else ''}{delta}%"
                subprocess.run(cmd, shell=True)
            elif system == "darwin":
                vol_cmd = f"set volume output volume (output volume of (get volume settings) + {delta})"
                subprocess.run(["osascript", "-e", vol_cmd])
            return f"[System] Volume {'increased' if delta>0 else 'decreased'}."
        except Exception as e:
            return f"[System] Volume error: {e}"

    def _mute(self, system: str) -> str:
        try:
            if system == "windows":
                import pyautogui
                pyautogui.press("volumemute")
            elif system == "linux":
                subprocess.run("pactl set-sink-mute @DEFAULT_SINK@ toggle", shell=True)
            return "[System] Audio toggled."
        except Exception as e:
            return f"[System] Mute error: {e}"

    def _open_app(self, command: str) -> str:
        import re
        app = re.sub(r'\b(open|launch|start)\b', '', command).strip()
        if not app:
            return "[System] No application specified."
        try:
            system = platform.system().lower()
            if system == "windows":
                _os.startfile(app)
            elif system == "linux":
                subprocess.Popen([app])
            elif system == "darwin":
                subprocess.Popen(["open", "-a", app])
            return f"[System] Opening {app}."
        except Exception as e:
            return f"[System] Could not open '{app}': {e}"

    def _shutdown(self, system: str) -> str:
        import time
        time.sleep(5)
        if system == "windows":
            subprocess.run("shutdown /s /t 1", shell=True)
        else:
            subprocess.run(["shutdown", "-h", "now"])
        return "[System] Shutting down in 5 seconds."

    def _restart(self, system: str) -> str:
        import time
        time.sleep(5)
        if system == "windows":
            subprocess.run("shutdown /r /t 1", shell=True)
        else:
            subprocess.run(["reboot"])
        return "[System] Restarting in 5 seconds."

    def _battery(self) -> str:
        try:
            import psutil
            b = psutil.sensors_battery()
            if b:
                return f"[System] Battery: {b.percent:.0f}%, {'charging' if b.power_plugged else 'discharging'}."
            return "[System] No battery detected."
        except Exception:
            return "[System] Battery info unavailable."

    def _system_stats(self) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            return (
                f"[System] CPU: {cpu}% | "
                f"RAM: {ram.percent}% used "
                f"({ram.used//1024//1024} MB / {ram.total//1024//1024} MB)"
            )
        except Exception:
            return "[System] Stats unavailable."
