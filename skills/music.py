"""
skills/music.py — Spotify playback control via spotipy.
"""

import re
import webbrowser
from core.config import CONFIG
from core.logger import log

class MusicSkill:
    """
    Spotify playback control via spotipy.

    INSTALL:
        pip install spotipy

    SETUP:
        1. Go to developer.spotify.com → Create App
        2. Set Redirect URI to: http://localhost:8888/callback
        3. Add spotify_client_id, spotify_client_secret to config.json
        4. First run opens browser for Spotify auth
    """

    triggers = [
        "play", "music", "song", "pause", "next", "previous",
        "volume up", "volume down", "playlist", "spotify", "skip",
        "resume", "track", "stop music", "set volume"
    ]

    def __init__(self):
        self._sp = None  # lazy-init to avoid blocking startup

    def _get_sp(self):
        if self._sp:
            return self._sp
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            
            cid = CONFIG.get("spotify_client_id", "")
            sec = CONFIG.get("spotify_client_secret", "")
            
            if not cid or not sec or "GET_FROM" in cid or "GET_FROM" in sec:
                log.warning("[MusicSkill] Missing Spotify credentials in config.json")
                return None
                
            self._sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id     = cid,
                client_secret = sec,
                redirect_uri  = "http://localhost:8888/callback",
                scope="user-modify-playback-state user-read-playback-state"
            ))
            return self._sp
        except ImportError:
            log.error("[MusicSkill] spotipy library not found. Install with: pip install spotipy")
            return None
        except Exception as e:
            log.error(f"Spotify init error: {e}")
            return None

    def handle(self, command: str) -> str:
        command = command.lower()

        # Handle opening browser Spotify regardless of API auth
        if "open spotify" in command or ("spotify" in command and any(w in command for w in ["open", "launch", "start"])):
            webbrowser.open("https://open.spotify.com/")
            return "[Music] Opening Spotify in your browser."

        sp = self._get_sp()
        if not sp:
            return "[Music] Spotify credentials missing. Add them to config.json."

        try:
            # Pause/Stop
            if "pause" in command or "stop music" in command:
                sp.pause_playback()
                return "[Music] Playback paused."

            # Skip / Next
            elif "next" in command or "skip" in command:
                sp.next_track()
                return "[Music] Skipped to next track."

            # Back / Previous
            elif "previous" in command or "back" in command:
                sp.previous_track()
                return "[Music] Playing previous track."

            # Resume
            elif "resume" in command:
                sp.start_playback()
                return "[Music] Playback resumed."

            # Volume Control
            elif "volume up" in command:
                current = self._get_current_volume(sp)
                new_vol = min(100, current + 15)
                sp.volume(new_vol)
                return f"[Music] Spotify volume set to {new_vol}%."

            elif "volume down" in command:
                current = self._get_current_volume(sp)
                new_vol = max(0, current - 15)
                sp.volume(new_vol)
                return f"[Music] Spotify volume set to {new_vol}%."

            elif "set volume" in command or "spotify volume to" in command:
                m = re.search(r'(\d+)', command)
                if m:
                    vol = int(m.group(1))
                    vol = max(0, min(100, vol))
                    sp.volume(vol)
                    return f"[Music] Spotify volume set to {vol}%."

            # Play / Search & Play
            elif "play" in command or "search" in command:
                query = re.sub(r'\b(play|music|song|on spotify|search for|search)\b', '', command).strip()
                
                if not query:
                    # Bare "play" command -> Resume
                    sp.start_playback()
                    return "[Music] Resuming playback."
                
                # Determine search type (playlist vs track)
                stype = "track"
                if "playlist" in command:
                    stype = "playlist"
                    query = query.replace("playlist", "").strip()
                
                results = sp.search(q=query, limit=1, type=stype)
                
                if stype == "track":
                    tracks = results.get("tracks", {}).get("items", [])
                    if tracks:
                        uri = tracks[0]["uri"]
                        sp.start_playback(uris=[uri])
                        name   = tracks[0]["name"]
                        artist = tracks[0]["artists"][0]["name"]
                        return f"[Music] Now playing: {name} by {artist}."
                    else:
                        return f"[Music] Could not find '{query}' on Spotify."
                else:
                    playlists = results.get("playlists", {}).get("items", [])
                    if playlists:
                        uri = playlists[0]["uri"]
                        sp.start_playback(context_uri=uri)
                        name = playlists[0]["name"]
                        return f"[Music] Now playing playlist: {name}."
                    else:
                        return f"[Music] Could not find playlist '{query}'."

            return "[Music] Command not understood."

        except Exception as e:
            error_str = str(e).lower()
            log.error(f"MusicSkill error: {e}")
            
            if "no active device" in error_str or "restriction_violated" in error_str:
                return "[Music] No active Spotify device found. Please open Spotify on your device and play something first."
            
            return f"[Music] An error occurred: {str(e)}"

    def _get_current_volume(self, sp) -> int:
        """Helper to fetch current device volume or default if unavailable."""
        try:
            devs = sp.devices()
            for d in devs.get('devices', []):
                if d.get('is_active'):
                    return d.get('volume_percent', 50)
        except:
            pass
        return 50
