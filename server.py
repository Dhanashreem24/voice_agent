import logging
import sys
import uuid
import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather

# ADK Imports
try:
    from agents.root_agent import root_agent
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from agents.root_agent import root_agent
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import Runner
    
    # GenAI Types
    from google.genai.types import Content, Part
    
except ImportError as e:
    logging.critical(f"Failed to import ADK components: {e}")
    sys.exit(1)

# --- Logging Setup ---
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

    # --- LATENCY MASKING ---
    # Instead of processing immediately (silence), we say something nice,
    # then Redirect to the actual processing endpoint.
    
    # Professional filler phrase
    resp.say("Thank you. Please bear with me for a moment.")
    resp.redirect('/process_speech')
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process_speech")
async def process_speech(request: Request):
    """
    Actual Agent Execution step.
    Called via TwiML <Redirect> after the acknowledgement.
    """
    form = await request.form()
    # In a redirect, the 'From' should preserved if sent by Twilio, 
    # but let's be robust.
    user_id = form.get("From", "local_tester")
    
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

    resp = VoiceResponse()

    try:
        # Construct Content object
        content_obj = Content(role="user", parts=[Part(text=user_text)])
        
        # 3. Use ADK Runner to handle the conversation loop (including tool calls)
        # Runner.run handles session retrieval/creation if we pass session_id.
        # It also handles the tool execution loop automatically.
        
        # Initialize Runner (one per request or global, doing per request for safety with current session logic)
        runner = Runner(
            agent=root_agent,
            app_name="voice-agent",
            session_service=session_service
        )

        agent_reply = ""
        logger.info("Invoking ADK Agent via Runner...")
        
        # Get or Create Session
        if user_id in USER_SESSION_MAP:
            session_id = USER_SESSION_MAP[user_id]
            logger.info(f"Resuming session: {session_id}")
        else:
            logger.info("Creating new session...")
            session = await session_service.create_session(
                app_name="voice-agent",
                user_id=user_id
            )
            session_id = session.id
            USER_SESSION_MAP[user_id] = session_id
            logger.info(f"Created new session: {session_id}")

        # Runner.run yields events. We iterate to find the final text response.
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content_obj
        ):
             logger.debug(f"Event Received: {type(event)} - {event}")
             
             # Extract text
             if hasattr(event, "text") and event.text:
                 agent_reply += event.text
             elif hasattr(event, "delta") and hasattr(event.delta, "text") and event.delta.text:
                 agent_reply += event.delta.text
             elif hasattr(event, "content") and event.content:
                 # Check if content is a Content object with parts
                 if hasattr(event.content, "parts") and event.content.parts:
                     for part in event.content.parts:
                         if hasattr(part, "text") and part.text:
                             agent_reply += part.text
                         elif hasattr(part, "function_call") and part.function_call:
                             logger.info(f"Runner executing FunctionCall: {part.function_call.name}")
                 else:
                     logger.debug(f"Ignored non-text content event: {event.content}")
             
             # Note: Runner handles the re-entry for tool results automatically.
             # We just watch the stream until it finishes.
        
        logger.info(f"Agent Response: '{agent_reply}'")

        if not agent_reply:
             agent_reply = "I'm thinking, but I have no response."

        
        # 6. Respond TwiML
        resp.say(agent_reply)
        gather = Gather(input='speech', action='/gather_speech', timeout=3)
        resp.append(gather)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        resp.say("I'm sorry, I ran into an error.")

    return Response(content=str(resp), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
