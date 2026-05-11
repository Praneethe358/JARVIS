import speech_recognition as sr
import os
import warnings
import audioop

# Suppress warnings and stderr to avoid flood
warnings.filterwarnings("ignore")

def get_rms(audio_data, sample_width):
    try:
        return audioop.rms(audio_data, sample_width)
    except:
        return 0

def scan_mics():
    print("="*60)
    print("   AUTOMATED MICROPHONE ENERGY SCAN")
    print("="*60)
    
    r = sr.Recognizer()
    mic_names = sr.Microphone.list_microphone_names()
    
    results = []
    
    for i, name in enumerate(mic_names):
        # Simple skip of HDMI and other known outputs usually
        if any(excl in name.lower() for excl in ["hdmi", "surround", "dmix"]):
            print(f"Skipping likely output device ID {i}: {name}")
            continue
            
        print(f"\nTesting ID {i}: {name}")
        
        # Suppress stderr for the test
        devnull = os.open(os.devnull, os.O_WRONLY)
        saved = os.dup(2)
        os.dup2(devnull, 2)
        
        try:
            m = sr.Microphone(device_index=i)
            with m as source:
                # Record 1.5 seconds
                audio = r.record(source, duration=1.5)
                # Calculate RMS energy directly from raw bytes
                energy = get_rms(audio.get_raw_data(), audio.sample_width)
                os.dup2(saved, 2) # restore log
                print(f"   -> CAPTURED! Average Energy Level: {energy}")
                results.append((i, name, energy))
        except Exception as e:
            os.dup2(saved, 2) # restore log
            print(f"   -> ERROR OPENING: {e}")
        finally:
            os.close(devnull)
            os.close(saved)
            
    print("\n" + "="*60)
    print("   FINAL REPORT")
    print("="*60)
    # Sort by energy descending
    sorted_res = sorted(results, key=lambda x: x[2], reverse=True)
    for rank, (i, name, val) in enumerate(sorted_res):
        status = "ACTIVE (POSSIBLE VOICE)" if val > 100 else "NEAR SILENCE"
        if val == 0: status = "ABSOLUTE ZERO (DEAD)"
        print(f"Rank #{rank+1}: ID {i} | Energy: {val:5d} | {status} | Name: {name}")

if __name__ == "__main__":
    scan_mics()
