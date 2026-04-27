"""
core/wake_word.py
─────────────────
Wake Word Detection — listens passively for "Hey JARVIS".

Method A (Recommended — free): Porcupine by Picovoice
    pip install pvporcupine pyaudio
    Free tier allows one custom wake word on local device.

Method B (Fallback): Keyword spotting via SpeechRecognition
    No API key needed, slightly higher CPU usage.

USAGE:
    detector = WakeWordDetector(keyword="jarvis")
    detector.listen()   # blocks until wake word detected
"""

import time
import speech_recognition as sr
from core.logger import log
from core.config import CONFIG


class WakeWordDetector:

    def __init__(self, keyword: str = "jarvis"):
        self.keyword   = keyword.lower()
        self.backend   = CONFIG.get("wake_backend", "sr")  # "porcupine" or "sr"
        self._porcupine = None

        if self.backend == "porcupine":
            self._init_porcupine()
        else:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 250
            self.recognizer.dynamic_energy_threshold = True
            self.mic = sr.Microphone()

        log.info(f"WakeWordDetector ready — keyword: '{self.keyword}', backend: {self.backend}")

    # ──────────────────────────────────────────────────────
    # Public: block until wake word detected
    # ──────────────────────────────────────────────────────
    def listen(self):
        """Blocks until wake word is detected."""
        if self.backend == "porcupine" and self._porcupine:
            self._listen_porcupine()
        else:
            self._listen_sr()

    # ──────────────────────────────────────────────────────
    # Backend A: Porcupine (recommended)
    # ──────────────────────────────────────────────────────
    def _init_porcupine(self):
        try:
            import pvporcupine
            # Built-in keyword: "jarvis"  (available in free tier)
            self._porcupine = pvporcupine.create(keywords=["jarvis"])
            log.info("Porcupine wake word engine loaded.")
        except ImportError:
            log.warning("pvporcupine not installed. Falling back to SpeechRecognition.")
            self.backend = "sr"
            self.recognizer = sr.Recognizer()
            self.mic = sr.Microphone()
        except Exception as e:
            log.error(f"Porcupine init failed: {e}. Falling back.")
            self.backend = "sr"

    def _listen_porcupine(self):
        import pyaudio, struct
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length
        )
        log.info("Porcupine stream open — waiting for 'Hey JARVIS'")
        try:
            while True:
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                result = self._porcupine.process(pcm)
                if result >= 0:
                    log.info("Wake word detected via Porcupine!")
                    break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    # ──────────────────────────────────────────────────────
    # Backend B: SpeechRecognition keyword spotting
    # ──────────────────────────────────────────────────────
    def _listen_sr(self):
        """
        Continuously samples short audio chunks and checks for
        the keyword using Google STT. Works without any API key
        for short phrases.
        """
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

        while True:
            try:
                with self.mic as source:
                    # Short phrase limit = low latency wake detection
                    audio = self.recognizer.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=3
                    )
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    if self.keyword in text:
                        log.info(f"Wake word '{self.keyword}' detected in: '{text}'")
                        return
                except sr.UnknownValueError:
                    pass  # silence or noise — keep listening
                except sr.RequestError:
                    # Offline fallback: just wait and retry
                    time.sleep(1)

            except Exception as e:
                log.error(f"Wake word listener error: {e}")
                time.sleep(0.5)
