import pvporcupine
import pyaudio
import struct
import os
import time
import ChandreTheAssistant.chandre as chandre
from dotenv import load_dotenv

load_dotenv()


PV_ACCESS_KEY=os.getenv('PV_ACCESS_KEY')

# === CONFIGURATION ===
ACCESS_KEY = PV_ACCESS_KEY
keyword_path = "Hey-Bro_en_mac_v3_0_0.ppn"
model_path = "porcupine_params.pv"

def initialize_audio_stream(porcupine):
    """Initialize or reinitialize the audio stream"""
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    return pa, stream

def cleanup_audio(pa, stream):
    """Clean up audio resources"""
    try:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        pa.terminate()
    except Exception as e:
        print(f"Error during audio cleanup: {e}")

# === Initialize Porcupine ===
porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[keyword_path],
    model_path=model_path
)

print("🎙️ Listening for wake word 'Hey Bro'...")

try:
    while True:
        # Initialize audio stream
        pa, stream = initialize_audio_stream(porcupine)
        
        try:
            while True:
                # Check if stream is still active
                if not stream.is_active():
                    print("⚠️ Audio stream inactive, reinitializing...")
                    break
                
                try:
                    pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                    
                    keyword_index = porcupine.process(pcm)
                    if keyword_index >= 0:
                        print("🔔 Wake word detected!")
                        
                        # Clean up current audio stream before calling assistant
                        cleanup_audio(pa, stream)
                        
                        try:
                            # Call your assistant's logic
                            chandre.main()
                        except Exception as e:
                            print(f"Error in assistant: {e}")
                        
                        print("🎙️ Listening for wake word again...")
                        break  # Break inner loop to reinitialize audio
                        
                except Exception as e:
                    print(f"Audio read error: {e}")
                    time.sleep(0.1)  # Brief pause before retrying
                    break
                    
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            cleanup_audio(pa, stream)
            
        # Brief pause before reinitializing
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Stopping...")
finally:
    if 'porcupine' in locals():
        porcupine.delete()
    print("Cleanup complete.")