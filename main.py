"""
╔══════════════════════════════════════════════════════════╗
║        J.A.R.V.I.S  —  Personal AI Assistant            ║
║  Just A Rather Very Intelligent System                   ║
║  Author : Praneeth | Stack : Python 3.11+                ║
╚══════════════════════════════════════════════════════════╝

ENTRY POINT — run this file to start JARVIS.
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
            AnalyticsSkill(),
            StudySkill(),
        ]
        self.router = CommandRouter(skills, self.brain)

        log.info("All systems online. JARVIS ready.")

    # ──────────────────────────────────────────────────────
    def run(self):
        self.voice.speak("JARVIS online. Awaiting your command, Praneeth.")

        while True:
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
