"""
stt_parakeet.py
───────────────
Speech-to-Text module using NVIDIA Parakeet (parakeet-tdt-0.6b-v2).
Records audio from microphone using sounddevice with Voice Activity Detection (webrtcvad)
to automatically stop on silence.
"""

import io
import wave
import time
import requests
import webrtcvad
import numpy as np
import sounddevice as sd
from config import NVIDIA_STT_URL, NVIDIA_STT_HEADERS, SAMPLE_RATE, CHANNELS, VAD_MODE, SILENCE_TIMEOUT_SEC, MAX_RECORD_SEC

class ParakeetSTT:
    def __init__(self):
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(VAD_MODE)
        self.sample_rate = SAMPLE_RATE
        self.channels = CHANNELS
        # webrtcvad requires 10, 20, or 30 ms frames. We'll use 30ms.
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * (self.frame_duration_ms / 1000.0))

    def _record_audio(self) -> bytes:
        """Records audio until silence is detected, returns WAV bytes."""
        print("\r[🎙️ ] Listening... Speak now.")
        
        frames = []
        silence_frames = 0
        speech_started = False
        max_frames = int((MAX_RECORD_SEC * 1000) / self.frame_duration_ms)
        silence_threshold = int((SILENCE_TIMEOUT_SEC * 1000) / self.frame_duration_ms)

        stream = sd.RawInputStream(
            samplerate=self.sample_rate, 
            channels=self.channels, 
            dtype='int16',
            blocksize=self.frame_size
        )

        with stream:
            for _ in range(max_frames):
                data, overflowed = stream.read(self.frame_size)
                if overflowed:
                    pass
                
                # Convert raw bytes to numpy array for VAD
                audio_frame = bytes(data)
                frames.append(audio_frame)

                try:
                    is_speech = self.vad.is_speech(audio_frame, self.sample_rate)
                except Exception:
                    is_speech = False
                
                if is_speech:
                    speech_started = True
                    silence_frames = 0
                else:
                    if speech_started:
                        silence_frames += 1
                        
                # Stop if silence threshold is met after speech started
                if speech_started and silence_frames > silence_threshold:
                    break
        
        # Write frames to in-memory WAV file
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        wav_io.seek(0)
        return wav_io.read()

    def listen(self) -> str:
        """
        Record audio, send to Parakeet API, return transcribed text.
        """
        wav_bytes = self._record_audio()
        
        if len(wav_bytes) < 44 + (self.sample_rate * 2 * 0.5): # Too short (<0.5 sec)
            return ""

        print("\r[⚡] Transcribing (NVIDIA Parakeet)...")
        try:
            # NVIDIA API expects multipart/form-data for audio/wav
            # Actually, looking at NVIDIA docs for parakeet, we might need a specific format.
            # According to standard NVCF pexec: Send binary directly if it's the only payload,
            # or send a json if it expects base64 or URL. Wait, the prompt said:
            # "Send WAV to Parakeet API". Let's send the raw bytes as application/octet-stream 
            # or audio/wav if NVCF expects that. Let's try audio/wav.
            
            headers = NVIDIA_STT_HEADERS.copy()
            headers["Content-Type"] = "audio/wav"

            # Wait, NVIDIA endpoints via build.nvidia.com might expect a specific payload structure.
            # If standard API, passing audio bytes directly. 
            # I will send audio/wav payload directly.
            
            response = requests.post(
                NVIDIA_STT_URL,
                headers=headers,
                data=wav_bytes,
                timeout=10
            )
            response.raise_for_status()
            
            # Usually the response contains JSON with a "text" or "transcript" field
            data = response.json()
            
            # NVIDIA standard output is either {"data": [{"text": "..."}]} or just {"text": "..."}
            # Let's extract safely
            text = ""
            if "data" in data and len(data["data"]) > 0:
                text = data["data"][0].get("text", "")
            elif "text" in data:
                text = data["text"]
            elif "results" in data:
                text = data["results"][0].get("transcript", "")
            
            return text.strip()
            
        except requests.exceptions.RequestException as e:
            print(f"\r[🔴] STT Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return ""
        except Exception as e:
            print(f"\r[🔴] STT Error: {e}")
            return ""
