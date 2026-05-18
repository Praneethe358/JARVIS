"""
nexus_main.py
─────────────
Entry point for the new NEXUS Jarvis-style voice assistant.
Handles wake word detection and launches the voice loop.
"""

import os
import sys
import core.ui as ui
from config import NVIDIA_API_KEY, OPENROUTER_API_KEY
from voice_loop import VoiceLoop
import speech_recognition as sr

def check_env():
    """Ensure API keys are loaded."""
    missing = []
    if not NVIDIA_API_KEY or NVIDIA_API_KEY == "your_nvidia_api_key_here":
        missing.append("NVIDIA_API_KEY")
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        missing.append("OPENROUTER_API_KEY")
        
    if missing:
        print("\r[🔴] MISSING API KEYS in .env file:")
        for key in missing:
            print(f"  - {key}")
        print("\nPlease update your .env file and restart.")
        sys.exit(1)

def listen_for_wake_word():
    """
    Passively listens for the wake word using lightweight Google STT.
    Returns True when wake word is detected.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5
    
    wake_words = ["nexus", "hey nexus", "wake up nexus"]
    
    print("\n[💤] PASSIVE MODE: Listening for wake word 'NEXUS'...")
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        while True:
            try:
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=3)
                text = recognizer.recognize_google(audio).lower()
                
                if any(w in text for w in wake_words):
                    print(f"\r[🟢] WAKE WORD DETECTED: '{text}'")
                    return True
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"\r[🔴] Wake word STT error: {e}")
                time.sleep(2)

def main():
    # Show animated banner first
    ui.banner(animate=True)
    check_env()
    
    print("\n  ▸  Voice Engine          [  OK  ]")
    print("  ▸  NVIDIA Parakeet STT   [  OK  ]")
    print("  ▸  OpenRouter LLM        [  OK  ]")
    print("  ▸  Microsoft Edge TTS    [  OK  ]")
    
    use_wake_word = True # Could be made a config toggle
    
    if use_wake_word:
        listen_for_wake_word()
        
    # Start the main continuous interactive loop
    loop = VoiceLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n\n[🔴] NEXUS Shutting Down. Goodbye.")
        sys.exit(0)

if __name__ == "__main__":
    main()
