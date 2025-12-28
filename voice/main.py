import requests
import pyttsx3
import speech_recognition as sr
import time

# Configuration
SERVER_URL = "http://localhost:8000/local/chat"
USER_ID = "local_tester_01"

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening... (Speak now)")
        # Adjust for ambient noise
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            print("Recognizing...")
            return r.recognize_google(audio)
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

def chat_loop():
    print("--- Local Voice Agent Client ---")
    print(f"Connecting to {SERVER_URL}")
    
    while True:
        user_text = listen()
        if user_text:
            print(f"You said: {user_text}")
            
            # Send to server for processing
            try:
                resp = requests.post(SERVER_URL, json={"text": user_text, "user_id": USER_ID})
                if resp.status_code == 200:
                    data = resp.json()
                    agent_reply = data.get("reply", "")
                    print(f"Agent: {agent_reply}")
                    speak(agent_reply)
                else:
                    print(f"Server Error: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Network Error: {e}")
        else:
            print("No speech detected.")
            # Optional: Don't loop infinitely fast on silence
            time.sleep(1)

if __name__ == "__main__":
    # Allow user to specify port via input or args if needed, but for now hardcoded to match test
    try:
        chat_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
