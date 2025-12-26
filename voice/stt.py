import speech_recognition as sr

def speech_to_text(timeout: int = 5, phrase_time_limit: int = 10):
    """
    Listens to the microphone and returns recognized text.
    """
    recognizer = sr.Recognizer()

    # Use the default microphone (choose correct index if multiple)
    mic = sr.Microphone()  # You can use sr.Microphone(device_index=0) if needed

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = recognizer.recognize_google(audio)
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"STT API error: {e}")
            return ""
