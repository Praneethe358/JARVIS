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
        4. Place credentials.json in the nexus/ folder
        5. First run: browser opens → authorise access
    """

    triggers = ["calendar", "appointment", "meeting", "what's today",
                "agenda", "event", "add event"]

    LOCAL_EVENTS_FILE = "data/local_events.json"  # fallback if no Google auth

    def __init__(self):
        self._events = self._load_local()

    def handle(self, command: str) -> str:
        if any(w in command for w in ["add event", "create event", "set event"]):
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
# SEARCH SKILL
# ══════════════════════════════════════════════════════════════════════════════

import webbrowser


class SearchSkill:
    """DuckDuckGo web search — returns snippet, optionally opens browser."""

    triggers = ["search", "look up", "google", "find", "what is", "who is",
                "tell me about", "search for", "browse", "youtube", "on youtube",
                "play on youtube", "play song on youtube"]

    def handle(self, command: str) -> str:
        import re
        
        if "youtube" in command:
            import urllib.request
            import urllib.parse
            
            query = re.sub(r'\b(play|song|search|open|youtube|on youtube|for)\b', '', command).strip()
            if not query:
                webbrowser.open("https://www.youtube.com/")
                return "[Search] Opening YouTube."

            try:
                # Intelligent shortcut: Resolve first result for instant playback
                encoded = urllib.parse.quote(query)
                url = f"https://www.youtube.com/results?search_query={encoded}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=4) as response:
                    html = response.read().decode()
                video_ids = re.findall(r"watch\?v=(\S{11})", html)
                if video_ids:
                    webbrowser.open(f"https://www.youtube.com/watch?v={video_ids[0]}")
                    return f"[Search] Playing '{query}' on YouTube."
            except Exception:
                pass # Graceful fallback to search listing on connection blip

            # Secondary fallback: traditional search page
            webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
            return f"[Search] Searching '{query}' on YouTube."

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
                # Trim droning paragraphs down to conversational length
                snippet = abstract[:220]
                if len(abstract) > 220:
                    snippet = snippet.rsplit('.', 1)[0] + '.' if '.' in snippet else snippet.strip() + "..."
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
import shutil
import webbrowser


class SystemSkill:
    """OS-level controls: volume, open apps, shutdown, screenshots."""

    triggers = ["volume", "open", "launch", "shutdown", "restart", "screenshot",
                "battery", "cpu", "ram", "memory", "brightness", "terminal", "cmd", "command prompt", "lock", "lock screen"]

    def handle(self, command: str) -> str:
        system = platform.system().lower()

        if "screenshot" in command:
            return self._screenshot()

        elif "lock" in command:
            return self._lock_screen(system)

        elif any(w in command for w in ["volume up", "increase volume"]):
            return self._volume(+10, system)

        elif any(w in command for w in ["volume down", "decrease volume"]):
            return self._volume(-10, system)

        elif "mute" in command:
            return self._mute(system)

        elif "shutdown" in command:
            return self._shutdown(system)

        elif "restart" in command:
            return self._restart(system)

        elif "brightness" in command:
            return self._brightness(command, system)

        elif any(w in command for w in ["open", "launch", "terminal", "cmd"]):
            return self._open_app(command)

        elif "battery" in command:
            return self._battery()

        elif any(w in command for w in ["cpu", "ram", "memory"]):
            return self._system_stats()

        return "[System] Command not recognised."

    def _screenshot(self) -> str:
        try:
            import os
            import shutil
            os.makedirs("data", exist_ok=True)
            from datetime import datetime
            fname = f"data/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Prioritize native Linux backends for stability
            if platform.system().lower() == "linux":
                if shutil.which("gnome-screenshot"):
                    subprocess.run(["gnome-screenshot", "-f", fname], check=False)
                    if os.path.exists(fname):
                         return f"[System] Screenshot saved: {fname}"
                elif shutil.which("scrot"):
                    subprocess.run(["scrot", fname], check=False)
                    if os.path.exists(fname):
                         return f"[System] Screenshot saved: {fname}"

            import pyautogui
            pyautogui.screenshot(fname)
            return f"[System] Screenshot saved: {fname}"
        except Exception as e:
            return f"[System] Screenshot failed: {e}"

    def _lock_screen(self, system: str) -> str:
        try:
            if system == "windows":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            elif system == "linux":
                # Sequence common locking directives
                cmds = [
                    "loginctl lock-session",
                    "xdg-screensaver lock",
                    "gnome-screensaver-command -l",
                    "dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock"
                ]
                for c in cmds:
                    try:
                        # Run in shell so we can ignore output and errors cleanly
                        if subprocess.run(c, shell=True, stderr=subprocess.DEVNULL, timeout=2).returncode == 0:
                            break
                    except Exception:
                        continue
            elif system == "darwin":
                subprocess.run(["pmset", "displaysleepnow"])
            
            return "[System] Machine locked."
        except Exception as e:
            return f"[System] Lock failed: {e}"


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
        target = re.sub(r'\b(open|launch|start)\b', '', command).strip()
        if not target:
            return "[System] No application specified."
        try:
            system = platform.system().lower()
            target_lower = re.sub(r'\s+', ' ', target.lower()).strip()

            url_map = {
                "chatgpt": "https://chatgpt.com/",
                "chat gpt": "https://chatgpt.com/",
                "github": "https://github.com/",
                "git hub": "https://github.com/",
                "github.com": "https://github.com/",
                "spotify": "https://open.spotify.com/",
                "youtube": "https://youtube.com/",
                "you tube": "https://youtube.com/",
                "browser": "https://www.google.com/",
                "chrome browser": "https://www.google.com/",
            }

            app_map = {
                "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
                "google chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
                "browser": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
                "terminal": ["gnome-terminal", "x-terminal-emulator", "konsole", "alacritty", "kitty", "xterm"],
                "cmd": ["gnome-terminal", "x-terminal-emulator", "konsole", "alacritty", "kitty", "xterm"],
                "command prompt": ["gnome-terminal", "x-terminal-emulator", "konsole", "alacritty", "kitty", "xterm"],
            }

            if system == "windows":
                app_map["terminal"] = ["wt", "cmd", "powershell"]
                app_map["cmd"] = ["wt", "cmd", "powershell"]
                app_map["command prompt"] = ["wt", "cmd", "powershell"]

            if target_lower in url_map:
                webbrowser.open(url_map[target_lower])
                return f"[System] Opening {target.title()} in your browser."

            if target_lower in ["spotify", "open spotify"]:
                webbrowser.open("https://open.spotify.com/")
                return "[System] Opening Spotify in your browser."

            if system == "windows":
                if target_lower in url_map:
                    webbrowser.open(url_map[target_lower])
                elif target_lower in app_map:
                    for app_name in app_map[target_lower]:
                        if shutil.which(app_name):
                            subprocess.Popen([app_name])
                            break
                    else:
                        webbrowser.open(f"https://www.google.com/search?q={target.replace(' ', '+')}")
                else:
                    _os.startfile(target)
            elif system == "linux":
                if target_lower in app_map:
                    for app_name in app_map[target_lower]:
                        if shutil.which(app_name):
                            subprocess.Popen([app_name])
                            break
                    else:
                        webbrowser.open(f"https://www.google.com/search?q={target.replace(' ', '+')}")
                else:
                    try:
                        subprocess.Popen([target])
                    except FileNotFoundError:
                        webbrowser.open(f"https://www.google.com/search?q={target.replace(' ', '+')}")
            elif system == "darwin":
                if target_lower in url_map:
                    webbrowser.open(url_map[target_lower])
                else:
                    subprocess.Popen(["open", "-a", target])
            return f"[System] Opening {target}."
        except Exception as e:
            return f"[System] Could not open '{target}': {e}"

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

    def _brightness(self, command: str, system: str) -> str:
        try:
            import re
            match = re.search(r'(\d+)', command)
            val = int(match.group(1)) if match else 50
            val = max(0, min(100, val))
            
            if system == "linux":
                # Standard GNOME d-bus method
                cmd = f'gdbus call --session --dest org.gnome.SettingsDaemon.Power --object-path /org/gnome/SettingsDaemon/Power --method org.freedesktop.DBus.Properties.Set org.gnome.SettingsDaemon.Power.Screen Brightness "<int32 {val}>"'
                subprocess.run(cmd, shell=True, check=False)
                return f"[System] Brightness set to {val}%."
                
            elif system == "windows":
                # Attempt through powershell/wmi directly
                cmd = f'powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{val})'
                subprocess.run(cmd, shell=True, check=False)
                return f"[System] Brightness set to {val}%."

            return "[System] Brightness control not supported on this OS."
            
        except Exception as e:
            log.error(f"Brightness error: {e}")
            return f"[System] Could not change brightness: {e}"
