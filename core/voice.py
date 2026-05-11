"""
core/voice.py
─────────────
Voice Engine — handles both Speech-to-Text (STT) and Text-to-Speech (TTS).

STT  : Google Speech Recognition (online)  OR  Whisper offline model
TTS  : pyttsx3 (offline, zero latency)     OR  ElevenLabs (premium, natural)

INSTALL:
    pip install SpeechRecognition pyttsx3 pyaudio
    pip install whisper-offline             # optional: offline STT
    pip install elevenlabs                  # optional: premium TTS
"""

import os
import speech_recognition as sr
import pyttsx3
import threading
from typing import Optional
from core.logger import log
from core.config import CONFIG
import core.ui as ui


def _suppress_stderr():
    """Redirect fd 2 to /dev/null; return (devnull_fd, saved_fd) to restore."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved   = os.dup(2)
    os.dup2(devnull, 2)
    return devnull, saved


def _restore_stderr(devnull_fd, saved_fd):
    os.dup2(saved_fd, 2)
    os.close(devnull_fd)
    os.close(saved_fd)


class VoiceEngine:
    """
    Unified voice interface for NEXUS.

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
        self.backend = CONFIG.get("stt_backend", "google")
        self.recognizer = sr.Recognizer()
        # Dynamic seeding: Removed hardcoded high baseline that caused stuck listening. Let dynamic calibration scale automatically.
        self.recognizer.energy_threshold    = 1000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold     = 0.6   # Slightly faster cutoff for immediate transition

        self.mic: Optional[sr.Microphone] = None
        if self.backend == "typed":
            log.info("STT backend set to typed input mode.")
        else:
            try:
                devnull, saved = _suppress_stderr()
                try:
                    idx = CONFIG.get("mic_device_index")
                    # Try preferred/default first
                    try:
                        self.mic = sr.Microphone(device_index=idx)
                        with self.mic as source:
                            pass # verified
                        log.info(f"Successfully bonded to Mic Index {idx if idx is not None else 'Default'}")
                    except Exception:
                        # FALLBACK SCAN: Cycle 0-8 to find valid hardware
                        log.warning("Default mic path blocked. Scanning for open hardware port...")
                        found = False
                        for fallback_idx in range(9):
                            try:
                                self.mic = sr.Microphone(device_index=fallback_idx)
                                with self.mic as source:
                                    pass
                                log.info(f"Recovered! Connected to available Port {fallback_idx}")
                                found = True
                                break
                            except:
                                continue
                        if not found:
                            raise Exception("Total Hardware Lockdown: No readable audio inputs discovered.")

                    with self.mic as source:
                        # Robust noise footprint scan (increased to 1.2s for stable baseline)
                        self.recognizer.adjust_for_ambient_noise(source, duration=1.2)
                finally:
                    _restore_stderr(devnull, saved)
            except Exception as e:
                log.warning(f"Microphone unavailable. Falling back to typed input mode: {e}")
                self.backend = "typed"

        log.info("VoiceEngine initialised.")

    # ──────────────────────────────────────────────────────
    # TTS configuration
    # ──────────────────────────────────────────────────────
    def _configure_tts(self):
        voices = self.tts_engine.getProperty("voices")

        # Prefer bold, clear, deep male voice variants on Linux/eSpeak.
        preferred_candidates = [
            "gmw/en-us+m3",       # Deep male voice (bold & clear)
            "gmw/en-us+m2",       # Medium-deep male voice
            "gmw/en-gb-x-rp+m3", # British deep male
            "gmw/en-gb+m3",       # UK deep male
            "en-us+m3",
            "en-gb+m3",
            "en+m3",
        ]

        selected_voice = None
        for candidate in preferred_candidates:
            try:
                self.tts_engine.setProperty("voice", candidate)
                selected_voice = candidate
                break
            except Exception:
                continue

        if selected_voice is None:
            # Fall back to a standard English voice if the female variant is unavailable.
            for voice in voices:
                voice_name = f"{voice.name} {voice.id}".lower()
                if any(token in voice_name for token in ["english (america)", "english (great britain)", "english (received pronunciation)", "en-us", "en-gb"]):
                    selected_voice = voice.id
                    break

        if selected_voice:
            try:
                self.tts_engine.setProperty("voice", selected_voice)
                log.info(f"Selected TTS voice: {selected_voice}")
            except Exception as e:
                log.warning(f"Could not set preferred voice '{selected_voice}': {e}")

        # Moderate rate for bold, clear voice (faster than female variant)
        self.tts_engine.setProperty("rate",   CONFIG.get("tts_rate",   140))  # words/min - bolder delivery
        self.tts_engine.setProperty("volume", CONFIG.get("tts_volume", 1.0))

    # ──────────────────────────────────────────────────────
    # Speak
    # ──────────────────────────────────────────────────────
    def speak(self, text: str):
        """Convert text to speech (blocking)."""
        if not text:
            return
        log.debug(f"[NEXUS] → {text}")  # debug-only: goes to log file, not terminal
        ui.speak_box(text)
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
        if self.backend == "typed" or self.mic is None:
            typed = ui.prompt_command().strip()
            return typed.lower() if typed else None

        with ui.waveform_listen("Listening"):
            try:
                devnull, saved = _suppress_stderr()
                try:
                    with self.mic as source:
                        audio = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_limit
                        )
                finally:
                    _restore_stderr(devnull, saved)

                # ── Backend selection ──────────────────────────
                backend = self.backend

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
            # Show the user's spoken text in a styled box
            ui.user_box(f"🎙️  {text}")
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            log.error(f"Google STT API error: {e}")
            return None

    def _whisper_recognise(self, audio) -> str | None:
        """
        Offline STT using a local Whisper model (runs locally).
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
UPGRADE: Replace pyttsx3 with ElevenLabs for a natural, NEXUS-like voice.

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
