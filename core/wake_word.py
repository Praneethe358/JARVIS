"""
core/wake_word.py
─────────────────
Wake Word Detection — listens passively for "Hey NEXUS".

Method A (Recommended — free): Porcupine by Picovoice
    pip install pvporcupine pyaudio
    Free tier allows one custom wake word on local device.

Method B (Fallback): Keyword spotting via SpeechRecognition
    No API key needed, slightly higher CPU usage.

USAGE:
    detector = WakeWordDetector(keyword="nexus")
    detector.listen()   # blocks until wake word detected
"""

import time
import os
import speech_recognition as sr
from core.logger import log
from core.config import CONFIG
import core.ui as ui


def _suppress_stderr():
    """Return (devnull_fd, saved_stderr_fd) — caller must restore and close."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved  = os.dup(2)
    os.dup2(devnull, 2)
    return devnull, saved


def _restore_stderr(devnull_fd, saved_fd):
    os.dup2(saved_fd, 2)
    os.close(devnull_fd)
    os.close(saved_fd)


class WakeWordDetector:

    def __init__(self, keyword: str = "nexus"):
        self.keyword   = keyword.lower()
        self.backend   = CONFIG.get("wake_backend", "sr")  # "porcupine" | "sr" | "typed"
        self._porcupine = None
        self.recognizer = None
        self.mic = None

        if self.backend == "porcupine":
            self._init_porcupine()
        elif self.backend == "sr":
            self._init_sr_backend()
        else:
            self.backend = "typed"

        log.info(f"WakeWordDetector ready — keyword: '{self.keyword}', backend: {self.backend}")

    # ──────────────────────────────────────────────────────
    # Public: block until wake word detected
    # ──────────────────────────────────────────────────────
    def listen(self):
        """Blocks until wake word is detected."""
        if self.backend == "porcupine" and self._porcupine:
            self._listen_porcupine()
        elif self.backend == "typed":
            self._listen_typed()
        else:
            self._listen_sr()

    # ──────────────────────────────────────────────────────
    # Backend A: Porcupine (recommended)
    # ──────────────────────────────────────────────────────
    def _init_porcupine(self):
        try:
            import pvporcupine
            # Built-in keyword: "nexus"  (available in free tier)
            access_key = CONFIG.get("porcupine_access_key", "")
            if not access_key:
                log.warning("No Porcupine access key found in config. Falling back to SpeechRecognition.")
                self.backend = "sr"
                self._init_sr_backend()
                return

            self._porcupine = pvporcupine.create(access_key=access_key, keywords=["nexus"])
            log.info("Porcupine wake word engine loaded.")
        except ImportError:
            log.warning("pvporcupine not installed. Falling back to SpeechRecognition.")
            self.backend = "sr"
            self._init_sr_backend()
        except Exception as e:
            log.warning(f"Porcupine unavailable ({e}). Falling back to SpeechRecognition.")
            self.backend = "sr"
            self._init_sr_backend()

    def _init_sr_backend(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        try:
            devnull, saved = _suppress_stderr()
            try:
                idx = CONFIG.get("mic_device_index")
                try:
                    self.mic = sr.Microphone(device_index=idx)
                    with self.mic as source:
                        pass 
                except Exception:
                    log.warning("Fallback Scan triggered in Wake Engine...")
                    found = False
                    for fallback_idx in range(9):
                        try:
                            self.mic = sr.Microphone(device_index=fallback_idx)
                            with self.mic as source:
                                pass
                            found = True
                            break
                        except:
                            continue
                    if not found:
                        raise Exception("Zero usable hardware found in Wake cycle.")
            finally:
                _restore_stderr(devnull, saved)
        except Exception as e:
            self.mic = None
            log.warning(f"Wake word microphone unavailable. Using typed wake word mode: {e}")
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
        log.info("Porcupine stream open — waiting for 'Hey NEXUS'")
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
        if self.mic is None:
            while True:
                typed = ui.prompt_wake().strip().lower()
                if self.keyword in typed:
                    log.info(f"Wake word '{self.keyword}' detected from typed input.")
                    return
            
        devnull, saved = _suppress_stderr()
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        finally:
            _restore_stderr(devnull, saved)

        while True:
            try:
                log.debug("Initiating fast 2.2-second raw capture (optimized performance)...")
                devnull, saved = _suppress_stderr()
                try:
                    with self.mic as source:
                        # Faster turnaround window: 2.2s cuts input latency nearly in half
                        audio = self.recognizer.record(source, duration=2.2)
                finally:
                    _restore_stderr(devnull, saved)
                
                log.debug("Audio chunk captured. Sending to Google STT...")
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    log.debug(f"STT heard: '{text}'")
                    if self.keyword in text:
                        log.info(f"Wake word '{self.keyword}' detected in: '{text}'")
                        return
                except sr.UnknownValueError:
                    log.debug("STT returned UnknownValueError (no speech detected or unintelligible).")
                    pass  # silence or noise — keep listening
                except sr.RequestError as e:
                    log.debug(f"STT RequestError: {e}")
                    # Offline fallback: just wait and retry
                    time.sleep(1)

            except Exception as e:
                log.error(f"Wake word listener error: {e}")
                time.sleep(0.5)

    def _listen_typed(self):
        while True:
            typed = ui.prompt_wake().strip().lower()
            if self.keyword in typed:
                log.info(f"Wake word '{self.keyword}' detected from typed input.")
                return
