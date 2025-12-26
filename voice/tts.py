import pyttsx3
import os

# Force 'espeak' driver on Linux
engine = pyttsx3.init(driverName='espeak')
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text: str):
    """
    Speak the text out loud.
    Uses pyttsx3 with espeak driver on Linux.
    """
    # Save temporary WAV and play via 'aplay' to guarantee Linux output
    temp_file = "/tmp/voice_agent_speech.wav"
    engine.save_to_file(text, temp_file)
    engine.runAndWait()

    # Use 'aplay' to ensure it goes through the default ALSA device
    os.system(f"aplay {temp_file}")
