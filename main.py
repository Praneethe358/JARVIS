"""
╔════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║    ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗                      ║
║    ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝                      ║
║    ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗                      ║
║    ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║                      ║
║    ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║                      ║
║    ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝                      ║
║                                                                        ║
║           🎯 Personal AI Assistant Platform v2.0                     ║
║         Neural EXecution & Unified System Automation                 ║
║                                                                        ║
║         👤 User: Praneeth | 📍 City: Coimbatore                     ║
║         🔧 Backend: Python 3.12+ | 🎙️  Voice: Deep Male             ║
║         💾 Storage: Local JSON | 🚀 Mode: Typed I/O                 ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝

QUICK START — run this file to start NEXUS.
    python main.py
"""

import time
import os
import sys
import threading
import core.ui as ui
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

class NEXUS:
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
        # Show animated banner first
        ui.banner(animate=True)

        log.info("Initialising NEXUS subsystems...")
        # Suppress ALSA/JACK noise from PyAudio by redirecting stderr during init
        _devnull = os.open(os.devnull, os.O_WRONLY)
        _old_stderr = os.dup(2)
        os.dup2(_devnull, 2)

        # ── Core engines ──────────────────────────────────
        self.voice   = VoiceEngine()
        self.brain   = Brain()
        self.wake    = WakeWordDetector(keyword="nexus")
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

        # Restore stderr
        os.dup2(_old_stderr, 2)
        os.close(_devnull)
        os.close(_old_stderr)

        # Animated boot sequence
        ui.boot_sequence()
        log.info("All systems online. NEXUS ready.")

    # ──────────────────────────────────────────────────────
    def _show_startup_menu(self):
        """Display interactive startup menu — delegates to core.ui."""
        ui.startup_menu()

    def run(self):
        """Main event loop with premium terminal UI."""
        from core.config import CONFIG
        
        # Only show menu in typed mode
        is_voice_mode = CONFIG.get("stt_backend") != "typed"
        if not is_voice_mode:
            self._show_startup_menu()
        
        if is_voice_mode:
            ui.status("VOICE MODE ACTIVE — listening for 'nexus' wake word", "wait")
        
        self.voice.speak("NEXUS online. Awaiting your command, Praneeth.")
        ui.divider()
        ui.status("NEXUS ACTIVE", "ok")
        ui.divider()

        _last_reminder_check = 0  # epoch seconds; 0 forces check on first iteration

        while True:
            # Check due reminders at most once every 60 seconds
            if self.personal and (time.time() - _last_reminder_check >= 60):
                for reminder in self.personal.check_due_reminders():
                    ui.reminder_box(reminder)   # styled orange alert
                    self.voice.speak(reminder)
                _last_reminder_check = time.time()

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

            log.debug(f"Command received: {command}")

            # 4. Route and execute (with spinner)
            response = ""
            with ui.spinner("Thinking"):
                response = self.router.handle(command)

            # 5. Speak response
            self.voice.speak(response)

            if any(w in command.lower() for w in ["exit", "shutdown nexus", "goodbye"]):
                log.info("Shutdown command received. Exiting main loop.")
                ui.shutdown_banner(CONFIG.get("user_name", "Praneeth"))
                break

            # 6. Log analytics
            self.router.analytics.log_interaction(command, response)


if __name__ == "__main__":
    nexus = NEXUS()
    nexus.run()
