import requests
import speech_recognition as sr
import pyttsx3
import time
import sys
import logging
from bs4 import BeautifulSoup

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Tester] %(message)s")
logger = logging.getLogger("LocalTester")

# --- Configuration ---
SERVER_URL = "http://localhost:8000"
GATHER_ENDPOINT = f"{SERVER_URL}/gather_speech"

def init_tts():
    engine = pyttsx3.init()
    # Optional: Adjust rate/volume
    # engine.setProperty('rate', 150)
    return engine

def speak(text, engine):
    logger.info(f"Speaking: {text}")
    print(f"\nAGENT: {text}\n")
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        logger.info("Adjusting for ambient noise... (Please wait)")
        r.adjust_for_ambient_noise(source, duration=1)
        
        print("\n[LISTENING] Speak now...")
        logger.info("Listening...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            logger.info("Processing audio...")
            text = r.recognize_google(audio)
            print(f"YOU: {text}")
            return text
        except sr.WaitTimeoutError:
            logger.warning("No speech detected (Timeout)")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except Exception as e:
            logger.error(f"Microphone Error: {e}")
            return None

def send_to_server(text):
    try:
        payload = {'SpeechResult': text}
        logger.info(f"Sending to server: {text}")
        response = requests.post(GATHER_ENDPOINT, data=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Server Communication Error: {e}")
        return None

def parse_twiml(xml_content):
    soup = BeautifulSoup(xml_content, 'xml')
    # Twilio <Say> tags contain the speech
    say_tags = soup.find_all('Say')
    messages = [tag.text for tag in say_tags]
    return " ".join(messages)

def main():
    engine = init_tts()
    
    print("=== LOCAL VOICE TESTER (Virtual Twilio) ===")
    print(f"Target Server: {SERVER_URL}")
    print("Press Ctrl+C to exit.\n")

    # Initial interaction (Simulate /voice call start if needed, but we loop /gather_speech)
    # Let's just start the loop assuming the user initiates:
    
    first_run = True

    while True:
        try:
            if first_run:
               speak("System ready. Please say something to start.", engine)
               first_run = False
            
            user_text = listen()
            
            if user_text:
                xml_response = send_to_server(user_text)
                if xml_response:
                    agent_reply = parse_twiml(xml_response)
                    if agent_reply:
                        speak(agent_reply, engine)
                    else:
                        logger.warning("Server returned no <Say> content.")
            else:
                # Optional: Speak 'I didn't hear you' if desired, or just re-loop
                pass
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Loop Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
