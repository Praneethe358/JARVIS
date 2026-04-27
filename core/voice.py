"""
core/voice.py
─────────────
Voice Engine — handles both Speech-to-Text (STT) and Text-to-Speech (TTS).

STT  : Google Speech Recognition (online)  OR  OpenAI Whisper (offline)
TTS  : pyttsx3 (offline, zero latency)     OR  ElevenLabs (premium, natural)

INSTALL:
    pip install SpeechRecognition pyttsx3 pyaudio
    pip install openai-whisper              # optional: offline STT
    pip install elevenlabs                  # optional: premium TTS
"""

import speech_recognition as sr
import pyttsx3
import threading
from core.logger import log
from core.config import CONFIG


class VoiceEngine:
    """
    Unified voice interface for JARVIS.

    Usage:
        engine = VoiceEngine()
        engine.speak("Hello Praneeth")
        text = engine.listen()          # returns str or None
    """

    def __init__(self):
        # ── TTS setup ──────────────────────────────────────
        self.tts_engine = pyttsx3.init()
        self._configure_tts()

        # ── STT setup ──────────────────────────────────────
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold    = 300   # mic sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold     = 0.8   # seconds of silence = end

        self.mic = sr.Microphone()

        # Adjust for ambient noise once at startup
        with self.mic as source:
            log.info("Calibrating microphone for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        log.info("VoiceEngine initialised.")

    # ──────────────────────────────────────────────────────
    # TTS configuration
    # ──────────────────────────────────────────────────────
    def _configure_tts(self):
        voices = self.tts_engine.getProperty("voices")

        # Pick a male voice if available (more JARVIS-like)
        for v in voices:
            if "male" in v.name.lower() or "david" in v.name.lower():
                self.tts_engine.setProperty("voice", v.id)
                break

        self.tts_engine.setProperty("rate",   CONFIG.get("tts_rate",   175))  # words/min
        self.tts_engine.setProperty("volume", CONFIG.get("tts_volume", 0.9))

    # ──────────────────────────────────────────────────────
    # Speak
    # ──────────────────────────────────────────────────────
    def speak(self, text: str):
        """Convert text to speech (blocking)."""
        if not text:
            return
        log.info(f"[JARVIS] → {text}")
        print(f"\n🔊 JARVIS: {text}\n")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def speak_async(self, text: str):
        """Non-blocking speak — runs in a separate thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    # ──────────────────────────────────────────────────────
    # Listen  (STT)
    # ──────────────────────────────────────────────────────
    def listen(self, timeout: int = 10, phrase_limit: int = 15) -> str | None:
        """
        Capture microphone input and return transcribed text.

        Args:
            timeout      : seconds to wait for speech to begin
            phrase_limit : max seconds to record a single phrase

        Returns:
            str  — transcribed command (lowercase)
            None — if recognition fails
        """
        print("🎙  Listening...")
        try:
            with self.mic as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )

            # ── Backend selection ──────────────────────────
            backend = CONFIG.get("stt_backend", "google")

            if backend == "whisper":
                return self._whisper_recognise(audio)
            else:
                return self._google_recognise(audio)

        except sr.WaitTimeoutError:
            log.warning("No speech detected within timeout.")
            return None
        except Exception as e:
            log.error(f"listen() error: {e}")
            return None

    def _google_recognise(self, audio) -> str | None:
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"👤 You: {text}")
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            log.error(f"Google STT API error: {e}")
            return None

    def _whisper_recognise(self, audio) -> str | None:
        """
        Offline STT using OpenAI Whisper (runs locally).
        Better accuracy, works without internet.
        """
        try:
            import whisper, tempfile, os, soundfile as sf

            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio.get_wav_data())
                tmp = f.name

            model = whisper.load_model("base")  # options: tiny/base/small/medium
            result = model.transcribe(tmp)
            os.unlink(tmp)
            text = result["text"].strip().lower()
            print(f"👤 You (whisper): {text}")
            return text

        except ImportError:
            log.warning("Whisper not installed. Falling back to Google STT.")
            return self._google_recognise(audio)
        except Exception as e:
            log.error(f"Whisper error: {e}")
            return None


# ── ELEVENLABS TTS (optional premium upgrade) ───────────────────────────────
"""
UPGRADE: Replace pyttsx3 with ElevenLabs for a natural, JARVIS-like voice.

from elevenlabs import generate, play, set_api_key
set_api_key("YOUR_ELEVENLABS_API_KEY")

def speak_elevenlabs(text: str):
    audio = generate(
        text=text,
        voice="Josh",           # or "Arnold", "Antoni"
        model="eleven_monolingual_v1"
    )
    play(audio)
"""
