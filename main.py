"""
╔════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗                        ║
║      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝                        ║
║      ██║███████║██████╔╝██║   ██║██║███████╗                        ║
║      ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║                        ║
║      ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║                        ║
║      ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝                        ║
║                                                                        ║
║           🎯 Personal AI Assistant Platform v2.0                     ║
║         Just A Rather Very Intelligent System                        ║
║                                                                        ║
║         👤 User: Praneeth | 📍 City: Coimbatore                     ║
║         🔧 Backend: Python 3.12+ | 🎙️  Voice: Deep Male             ║
║         💾 Storage: Local JSON | 🚀 Mode: Typed I/O                 ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝

QUICK START — run this file to start JARVIS.
    python main.py
"""

import time
import threading
from core.voice      import VoiceEngine
from core.brain      import Brain
from core.wake_word  import WakeWordDetector
from core.face_auth  import FaceAuth
from skills.weather  import WeatherSkill
from skills.news     import NewsSkill
from skills.calendar_skill import CalendarSkill
from skills.music    import MusicSkill
from skills.search   import SearchSkill
from skills.system   import SystemSkill
from skills.notes    import NotesSkill
from skills.personal import PersonalAssistantSkill
from skills.analytics import AnalyticsSkill
from skills.study    import StudySkill
from core.router     import CommandRouter
from core.logger     import log

class JARVIS:
    """
    Central orchestrator.  Wires together all subsystems.

    Flow:
        Wake-word detected
            → Face verified (optional)
            → STT: mic → text
            → Router: text → skill or brain
            → Skill / Brain: text → response
            → TTS: response → audio
    """

    def __init__(self):
        log.info("Initialising JARVIS subsystems...")

        # ── Core engines ──────────────────────────────────
        self.voice   = VoiceEngine()
        self.brain   = Brain()
        self.wake    = WakeWordDetector(keyword="jarvis")
        self.face    = FaceAuth()

        # ── Skills ────────────────────────────────────────
        skills = [
            WeatherSkill(),
            NewsSkill(),
            CalendarSkill(),
            MusicSkill(),
            SearchSkill(),
            SystemSkill(),
            NotesSkill(),
            PersonalAssistantSkill(),
            AnalyticsSkill(),
            StudySkill(),
        ]
        self.router = CommandRouter(skills, self.brain)
        self.personal = next((s for s in skills if s.__class__.__name__ == "PersonalAssistantSkill"), None)

        log.info("All systems online. JARVIS ready.")

    # ──────────────────────────────────────────────────────
    def _show_startup_menu(self):
        """Display interactive startup menu with commands and shortcuts."""
        menu = """
╔════════════════════════════════════════════════════════════════════════╗
║                     📋 COMMAND REFERENCE                               ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎤 VOICE COMMANDS (say after "jarvis"):                              ║
║  ─────────────────────────────────────────────────────────────────   ║
║    💬 "who are you"              → Meet JARVIS                         ║
║    ⏰ "what's the time"          → Get current time                    ║
║    📅 "what's today's date"     → Get today's date                    ║
║    🎵 "play music"              → Spotify playback                    ║
║    🔍 "search [query]"          → Web search via DuckDuckGo           ║
║    📝 "take a note [text]"      → Save quick note                     ║
║    🔔 "remind me [task]"        → Set reminder with time              ║
║    📅 "add schedule [event]"    → Add work schedule item             ║
║    💡 "help"                    → List all features                   ║
║                                                                        ║
║  ⚡ SHORTCUTS (Typed Mode):                                            ║
║  ─────────────────────────────────────────────────────────────────   ║
║    wake word     → "jarvis" (in any text)                            ║
║    type command  → Enter command at prompt                            ║
║    exit          → "exit" or "goodbye" or "shutdown jarvis"          ║
║    clear memory  → "clear memory" or "reset brain"                  ║
║                                                                        ║
║  📚 SKILL CATEGORIES:                                                 ║
║  ─────────────────────────────────────────────────────────────────   ║
║    🌤️  Weather      → "weather", "forecast"                          ║
║    📰 News          → "news", "headlines", "latest"                  ║
║    🎼 Music         → "play", "pause", "next", "previous"            ║
║    🔍 Search        → "search", "look up", "find"                    ║
║    🖥️  System       → "volume", "open app", "screenshot"             ║
║    📔 Notes         → "note", "save", "list notes"                   ║
║    🎓 Study         → "quiz", "explain", "summarize"                 ║
║    ⏰ Reminders     → "reminder", "schedule", "task"                 ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝

"""
        print(menu)
        print("\n" + "="*76)
        print(f"{'═':^76}")
        print(f"{'🎯 Press Enter to begin. Say "jarvis" to wake me up.':^76}")
        print(f"{'═':^76}")
        print("="*76 + "\n")
        input("\n>>> Ready? Press Enter to start...")

    def run(self):
        """Main event loop with modern terminal UI."""
        # Show startup menu with commands
        self._show_startup_menu()
        
        self.voice.speak("JARVIS online. Awaiting your command, Praneeth.")
        print("\n" + "─"*76)
        print(f"{'🟢 JARVIS ACTIVE':^76}")
        print("─"*76 + "\n")

        while True:
            if self.personal:
                for reminder in self.personal.check_due_reminders():
                    self.voice.speak(reminder)

            # 1. Block until wake word heard
            log.info("Listening for wake word...")
            self.wake.listen()

            # 2. Optional face verification
            if not self.face.verify():
                self.voice.speak("Face not recognised. Access denied.")
                continue

            # 3. Listen for command
            self.voice.speak("Yes?")
            command = self.voice.listen()
            if not command:
                self.voice.speak("I didn't catch that. Try again.")
                continue

            log.info(f"Command received: {command}")

            # 4. Route and execute
            response = self.router.handle(command)

            # 5. Speak response
            self.voice.speak(response)

            if any(w in command.lower() for w in ["exit", "shutdown jarvis", "goodbye"]):
                log.info("Shutdown command received. Exiting main loop.")
                break

            # 6. Log analytics
            self.router.analytics.log_interaction(command, response)


if __name__ == "__main__":
    jarvis = JARVIS()
    jarvis.run()
