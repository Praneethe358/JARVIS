import speech_recognition as sr
import time
import os
import sys

def diagnose():
    print("="*50)
    print("   NEXUS MICROPHONE DIAGNOSTIC UTILITY   ")
    print("="*50)
    print("\n1. Listing all available microphones detected by OS:")
    
    try:
        mic_list = sr.Microphone.list_microphone_names()
        for i, name in enumerate(mic_list):
            print(f"  ID {i}: {name}")
    except Exception as e:
        print(f"CRITICAL ERROR LISTING MICS: {e}")
        return

    print("\n2. Testing the DEFAULT microphone (will listen for 3 seconds):")
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    
    try:
        with sr.Microphone() as source:
            print("   >> CALIBRATING AMBIENT NOISE (Please be quiet for 2 seconds)...")
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"   >> Calibrated energy baseline: {r.energy_threshold:.2f}")
            
            print("\n   >> NOW PLEASE SPEAK INTO THE MIC CLEARLY! (Listening for 4 seconds)...")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=4)
                print("   >> AUDIO CAPTURED SUCCESSFULLY!")
                print("   >> Sending to Google for quick test recognition...")
                text = r.recognize_google(audio)
                print(f"   >> [SUCCESS] Recognized Text: '{text}'")
                print("\nVerdict: Your default microphone works perfectly with the Google engine!")
            except sr.WaitTimeoutError:
                print("   >> [FAILURE] No speech detected. Timed out waiting for input.")
                print("   >> Try adjusting your system microphone input volume or ensuring it isn't muted.")
            except sr.UnknownValueError:
                print("   >> [FAILURE] Captured sound, but Google couldn't understand it.")
                print("   >> Likely static, noise, or your voice was too faint.")
            except Exception as e:
                print(f"   >> [FAILURE] Google recognition returned error: {e}")
    except Exception as e:
        print(f"\nERROR opening default microphone: {e}")
        print("Try testing with explicit device IDs if listed above.")

if __name__ == "__main__":
    diagnose()
