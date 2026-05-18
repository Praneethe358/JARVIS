"""
voice_loop.py
─────────────
The main conversation orchestrator. 
Handles continuous voice turns, UI updates, and routing.
"""

from stt_parakeet import ParakeetSTT
from tts_edge import EdgeTTS
from llm_openrouter import OpenRouterLLM
from intent_router import IntentRouter
import core.ui as ui
import time

class VoiceLoop:
    def __init__(self):
        self.stt = ParakeetSTT()
        self.tts = EdgeTTS()
        self.llm = OpenRouterLLM()
        self.router = IntentRouter()

    def run(self):
        """Main continuous interaction loop."""
        ui.divider()
        ui.status("NEXUS ACTIVE", "ok")
        ui.divider()

        # Speak an initial greeting
        greeting = "NEXUS online. Voice mode activated."
        ui.user_box("🎙️  (System started)")
        self._display_nexus_reply(greeting)
        self.tts.speak(greeting)

        while True:
            ui.status("LISTENING", "wait")
            
            # 1. Listen via Parakeet
            text = self.stt.listen()
            
            if not text:
                continue

            ui.user_box(f"🎙️  {text}")
            
            # Check for exit commands
            if any(w in text.lower() for w in ["exit", "shutdown nexus", "goodbye"]):
                reply = "Goodbye. Shutting down."
                self._display_nexus_reply(reply)
                self.tts.speak(reply)
                break

            # 2. Intent Routing & Context fetching
            context = self.router.classify_and_contextualize(text)
            
            # 3. Think via OpenRouter
            ui.status("THINKING", "wait")
            reply = self.llm.generate(text, context)
            
            # 4. Speak response
            ui.status("SPEAKING", "wait")
            
            # Post-process for Browser intent
            if reply.startswith("[BROWSER:"):
                try:
                    import webbrowser
                    url = reply.replace("[BROWSER:", "").replace("]", "").strip()
                    webbrowser.open(url)
                    reply = "Opening that in your browser."
                except Exception as e:
                    reply = f"I tried to open the browser but encountered an error."

            self._display_nexus_reply(reply)
            self.tts.speak(reply)
            
            ui.status("NEXUS READY", "ok")

    def _display_nexus_reply(self, text: str):
        """Displays the NEXUS response in the terminal aesthetic."""
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n╔ ◈ NEXUS · {now} ══════════════════════════════════════════╗")
        
        # Word wrap the text
        import textwrap
        lines = textwrap.wrap(text, width=58)
        for line in lines:
            print(f"║  {line:<58}║")
            
        print(f"╚══════════════════════════════════════════════════════════════╝\n")
