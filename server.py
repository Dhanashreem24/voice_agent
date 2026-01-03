import logging
import sys
import uuid
import os
import re

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather, Play
from twilio.rest import Client

# ADK Imports
try:
    from agents.root_agent import root_agent
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from agents.agent_factory import create_agent_graph
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import Runner
    
    # GenAI Types
    from google.genai.types import Content, Part
    from google.adk.models.google_llm import Gemini
    
    # Load keys
    from dotenv import load_dotenv
    load_dotenv()
    
except ImportError as e:
    logging.critical(f"Failed to import ADK components: {e}")
    sys.exit(1)

# --- Logging Setup ---
# Force UTF-8 for Windows Consoles to support symbols like ₹
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("server.log")
    ]
)
logger = logging.getLogger("VoiceServer")

app = FastAPI(title="ADK Voice Agent")

# --- Twilio Client Setup (For Async Updates) ---
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_client = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("Twilio Client initialized.")
    except Exception as e:
        logger.error(f"Failed to init Twilio Client: {e}")

# --- API Key Rotation Setup ---
# Expects CSV string: "key1,key2,key3"
API_KEYS_STR = os.environ.get("GOOGLE_API_KEYS", "")
API_KEYS = [k.strip() for k in API_KEYS_STR.split(",") if k.strip()]
if not API_KEYS and os.environ.get("GOOGLE_API_KEY"):
    API_KEYS.append(os.environ["GOOGLE_API_KEY"])

import random

def rotate_api_key():
    """Selects a random API key from the available pool and sets it in env."""
    if API_KEYS:
        selected_key = random.choice(API_KEYS)
        # Set into environment so Gemini / GoogleGenAI client picks it up
        os.environ["GOOGLE_API_KEY"] = selected_key
        logger.info(f"Rotated API Key: ...{selected_key[-4:]}")
    else:
        logger.warning("No API Keys configured for rotation.")

# Initialize Session Service
# InMemoryService is suitable for local dev/testing.
session_service = InMemorySessionService()

# Global Session Map for Voice Users (PhoneNumber -> SessionID)
USER_SESSION_MAP = {}
# Temporary stash for inputs during redirect loop
PENDING_INPUTS = {}

# Run Config
run_config = RunConfig(
    response_modalities=["text"]
)

def get_filler_message(text: str) -> str:
    """Determines a context-aware filler message based on user input."""
    text = text.lower()
    
    if re.search(r"(balance|bill|pay|cost|owing|due)", text):
        return "I am checking your account details, please wait a moment."
    
    if re.search(r"(internet|slow|down|outage|wifi|connect)", text):
        return "I am checking the network status in your area, one moment please."
        
    if re.search(r"(human|agent|operator|person|talk to|speak with|escalate)", text):
        return "I am connecting you to a human agent, please hold."
        
    return "Thank you. Please bear with me for a moment."

def is_goodbye(text: str) -> bool:
    """Checks if the user wants to end the call."""
    # Normalize: lowercase and remove punctuation (keep spaces)
    text = re.sub(r'[^\w\s]', '', text.lower()).strip()
    
    # Simple explicit phrases
    if text in ["bye", "goodbye", "cancel", "end", "hang up", "exit", "quit", "thanks bye", "thank you bye"]:
        return True
        
    # Regex for phrases
    if re.search(r"^(goodbye|bye|bye\s+bye|see\s+you|talk\s+to\s+you\s+later)$", text):
        return True
        
    if re.search(r"(thank\s+you|thanks)\s+(bye|goodbye)", text):
        return True
        
    return False

@app.post("/voice")
async def voice_start(request: Request):
    """
    Handle incoming calls.
    Returns TwiML to greet the user and start listening.
    """
    logger.info("Received new call /voice")
    
    resp = VoiceResponse()
    
    # 1. Greet the User
    intro_message = "Welcome to the Support Line. How can I help you today?"
    resp.say(intro_message)
    logger.info(f"Greeting User: '{intro_message}'")

    # 2. Listen for User Input
    gather = Gather(input='speech', action='/gather_speech', timeout=3)
    resp.append(gather)

    # 3. Fallback if no input
    resp.say("I didn't catch that. Goodbye!")
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/gather_speech")
async def gather_speech(request: Request):
    """
    Handle speech input captured by Twilio (or local tester).
    Passes text to Agent -> Gets Response -> Returns TwiML.
    Uses usage pattern similar to ADK Web.
    """
    form = await request.form()
    user_text = form.get("SpeechResult")
    # For local testing, 'From' might not be present or unique, so use a static ID or 'From'
    user_id = form.get("From", "local_tester")
    
    logger.info(f"Received Speech Input: '{user_text}' from {user_id}")

    resp = VoiceResponse()

    if not user_text:
        resp.say("I didn't hear anything.")
        gather = Gather(input='speech', action='/gather_speech', timeout=3)
        resp.append(gather)
        return Response(content=str(resp), media_type="application/xml")

    # Store input for the processing step
    PENDING_INPUTS[user_id] = user_text

    # --- INSTANT HANGUP CHECK ---
    # If user says "Goodbye", hang up immediately without invoking LLM
    if is_goodbye(user_text):
        logger.info(f"Detected Goodbye Intent from {user_id}. Hanging up.")
        resp.say("Thank you for calling. Goodbye!")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    # --- LATENCY MASKING ---
    # Instead of processing immediately (silence), we say something nice,
    # then Redirect to the actual processing endpoint.
    
    
    # Professional filler phrase
    filler = get_filler_message(user_text)
    resp.say(filler)
    resp.redirect('/process_speech')
    
    return Response(content=str(resp), media_type="application/xml")

async def get_agent_response(user_id: str, user_text: str) -> str:
    """Core logic to run the ADK Agent (Session + Runner)."""
    try:
        content_obj = Content(role="user", parts=[Part(text=user_text)])
        agent_reply = ""
        
        
        # 1. Get or Create Session (and Truncate History)
        if user_id in USER_SESSION_MAP:
            session_id = USER_SESSION_MAP[user_id]
            logger.info(f"Resuming session: {session_id}")
            
            # --- CONTEXT TRUNCATION ---
            try:
                current_session = await session_service.get_session(session_id)
                if current_session and hasattr(current_session, 'events'):
                    MAX_EVENTS = 15
                    if len(current_session.events) > MAX_EVENTS:
                        logger.info(f"Truncating history: {len(current_session.events)} -> {MAX_EVENTS}")
                        current_session.events = current_session.events[-MAX_EVENTS:]
            except Exception as e:
                logger.warning(f"Failed to truncate history: {e}")
        else:
            logger.info("Creating new session...")
            session = await session_service.create_session(
                app_name="voice-agent",
                user_id=user_id
            )
            session_id = session.id
            USER_SESSION_MAP[user_id] = session_id
            logger.info(f"Created new session: {session_id}")

        # 2. Key Rotation
        rotate_api_key()
        
        # 3. Create Agent (Dynamic Graph with User ID injected)
        agent_instance = create_agent_graph(user_id)
        
        # 4. Initialize Runner
        runner = Runner(
            agent=agent_instance,
            app_name="voice-agent",
            session_service=session_service
        )

        # 4. Execute Runner Loop
        logger.info("Starting Agent Execution...")
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content_obj
        ):
             # Extract text
             if hasattr(event, "text") and event.text:
                 agent_reply += event.text
             elif hasattr(event, "delta") and hasattr(event.delta, "text") and event.delta.text:
                 agent_reply += event.delta.text
             elif hasattr(event, "content") and event.content:
                 if hasattr(event.content, "parts") and event.content.parts:
                     for part in event.content.parts:
                         if hasattr(part, "text") and part.text:
                             agent_reply += part.text
                         elif hasattr(part, "function_call") and part.function_call:
                             logger.info(f"Runner executing FunctionCall: {part.function_call.name}")
        
        if not agent_reply:
             agent_reply = "I'm thinking, but I have no response."
             
        return agent_reply

    except Exception as e:
        logger.error(f"Error in agent execution: {e}", exc_info=True)
        return "I'm sorry, I encountered an error while processing your request."

async def handle_async_agent(user_id: str, user_text: str, call_sid: str, base_url: str):
    """Background Task: Runs agent -> Updates Live Call."""
    logger.info(f"Starting Async Agent logic for CallSid: {call_sid}")
    
    agent_response_text = await get_agent_response(user_id, user_text)
    
    logger.info(f"Async Agent Response Ready: '{agent_response_text}'")
    
    try:
        # Build TwiML to interrupt the hold music and speak result
        # NOTE: When pushing TwiML via API, relative URLs might fail. 
        # We must use the absolute URL for the Gather action.
        # Ensure base_url ends with slash or handle it
        if not base_url.endswith("/"):
            base_url += "/"
        gather_action_url = f"{base_url}gather_speech"
        
        new_twiml = VoiceResponse()
        new_twiml.say(agent_response_text)
        gather = Gather(input='speech', action=gather_action_url, timeout=3)
        new_twiml.append(gather)
        
        # Fallback if no speech
        new_twiml.redirect(gather_action_url)
        
        # Update the live call
        call = twilio_client.calls(call_sid).update(twiml=str(new_twiml))
        logger.info(f"Successfully updated Call {call_sid} with Agent Response.")
        
    except Exception as e:
        logger.error(f"Failed to update Twilio Call {call_sid}: {e}")


@app.post("/process_speech")
async def process_speech(request: Request, background_tasks: BackgroundTasks):
    """
    Decides between Sync (Local) and Async (Twilio) processing.
    """
    form = await request.form()
    user_id = form.get("From", "local_tester")
    call_sid = form.get("CallSid")
    
    # Retrieve stashed input
    user_text = PENDING_INPUTS.get(user_id)
    
    if not user_text:
        logging.warning(f"No pending input found for {user_id}")
        resp = VoiceResponse()
        resp.say("I lost your connection. Please say that again.")
        resp.redirect('/voice') # Restart loop
        return Response(content=str(resp), media_type="application/xml")

    # Clear stash
    del PENDING_INPUTS[user_id]

    # --- DECISION: SYNC OR ASYNC? ---
    # use Sync if Local Tester OR Twilio Client not configured OR CallSid missing due to some reason
    is_local_test = (user_id == "local_tester") or ("local_tester" in user_id)
    can_use_async = (twilio_client is not None) and (call_sid is not None)
    
    if is_local_test or not can_use_async:
        logger.info(f"Running SYNCHRONOUSLY for {user_id}")
        # Blocking call
        agent_reply = await get_agent_response(user_id, user_text)
        
        resp = VoiceResponse()
        resp.say(agent_reply)
        gather = Gather(input='speech', action='/gather_speech', timeout=3)
        resp.append(gather)
        return Response(content=str(resp), media_type="application/xml")
        
    else:
        logger.info(f"Running ASYNCHRONOUSLY for {user_id} (CallSid: {call_sid})")
        
        # 1. Trigger Background Task
        # Pass the base_url so we can construct absolute callbacks
        base_url = str(request.base_url)
        background_tasks.add_task(handle_async_agent, user_id, user_text, call_sid, base_url)
        
        # 2. Return Hold Music TwiML immediately
        resp = VoiceResponse()
        # You can replace this logic with <Play>url_to_music</Play>
        # Loop the 'Please hold' message or pause
        resp.say("I am checking that for you, please hold on...")
        # Pause for 30 seconds
        resp.pause(length=30)
        # If 30s passes and nothing happens:
        resp.say("I am still thinking...")
        resp.pause(length=30)
        
        # Eventually give up if background task failed to update
        resp.say("I am taking longer than expected. Please try again later.")
        resp.hangup()
        
        return Response(content=str(resp), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
