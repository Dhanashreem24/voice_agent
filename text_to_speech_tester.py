import requests
import pyttsx3
import time
import sys
import logging
from bs4 import BeautifulSoup

# Setup Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("TextTester")

# Configuration
SERVER_URL = "http://localhost:8000/gather_speech"

def speak_text(text):
    """Synthesize text to speech using pyttsx3."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150) # Slower rate for clarity
        print(f"\nAGENT: {text}\n")
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logger.error(f"TTS Error: {e}")

def send_text_to_server(text):
    """Send text to the local Voice Agent server."""
    try:
        # Mimic Twilio's form data
        data = {
            'SpeechResult': text,
            'From': 'text_tester_user'
        }
        
        logger.info(f"Sending: '{text}'")
        response = requests.post(SERVER_URL, data=data)
        
        if response.status_code == 200:
            # Parse TwiML to find <Say>
            soup = BeautifulSoup(response.text, 'lxml') # use lxml or html.parser
            say_tags = soup.find_all('say')
            
            full_response = " ".join([tag.get_text() for tag in say_tags])
            
            if full_response:
                return full_response
            else:
                return "[No spoken response found in TwiML]"
        else:
            return f"Error: Server returned {response.status_code}"
            
    except Exception as e:
        return f"Connection Error: {e}"

def main():
    print("=== ADK VOICE AGENT - TEXT TESTER ===")
    print(f"Targeting: {SERVER_URL}")
    print("Type your message and press Enter.")
    print("Type 'exit' or 'quit' to stop.")
    print("=====================================")

    while True:
        try:
            user_input = input("\nYOU: ").strip()
            
            if user_input.lower() in ('exit', 'quit'):
                break
                
            if not user_input:
                continue

            # Send and Speak
            agent_response = send_text_to_server(user_input)
            speak_text(agent_response)
            
        except KeyboardInterrupt:
            break
            
    print("\nGoodbye!")

if __name__ == "__main__":
    main()
