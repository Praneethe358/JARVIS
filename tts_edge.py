"""
tts_edge.py
───────────
Text-to-Speech module using Microsoft edge-tts.
Outputs high-quality neural speech and plays directly to speakers
using sounddevice and pydub (in-memory, no files saved).
"""

import io
import asyncio
import edge_tts
import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from config import TTS_VOICE, TTS_RATE

class EdgeTTS:
    def __init__(self):
        self.voice = TTS_VOICE
        self.rate = TTS_RATE

    async def _generate_audio_bytes(self, text: str) -> bytes:
        """Asynchronously streams TTS data into memory."""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        audio_data = bytearray()
        
        # Stream the audio chunks directly to memory
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
                
        return bytes(audio_data)

    def speak(self, text: str):
        """
        Synchronous method to generate and play TTS audio.
        Converts MP3 bytes -> raw audio -> sounddevice playback.
        """
        if not text.strip():
            return

        print("\r[🔊] Speaking...")
        
        try:
            # Generate MP3 bytes using asyncio event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        try:
            mp3_bytes = loop.run_until_complete(self._generate_audio_bytes(text))
            
            if not mp3_bytes:
                return

            # Decode MP3 to raw audio using pydub
            audio_io = io.BytesIO(mp3_bytes)
            segment = AudioSegment.from_file(audio_io, format="mp3")
            
            # Extract raw audio data
            samples = np.array(segment.get_array_of_samples())
            
            # If stereo, pydub interleaves the array; reshape it
            if segment.channels == 2:
                samples = samples.reshape((-1, 2))
                
            # Play using sounddevice
            sd.play(samples, samplerate=segment.frame_rate)
            sd.wait() # Block until audio is fully played
            
        except Exception as e:
            print(f"\r[🔴] TTS Error: {e}")
            # Fallback could be implemented here (e.g., pyttsx3) if requested

    def speak_async(self, text: str):
        """Non-blocking speak in a background thread."""
        import threading
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
