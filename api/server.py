import uuid
import inspect
import logging
import urllib.parse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse, Gather

from google.adk.runners import InvocationContext, RunConfig
from google.adk.sessions import InMemorySessionService

from agents.root_agent import root_agent
from agents.billing_agent import billing_agent
from agents.tech_agent import tech_agent
from agents.escalation_agent import escalation_agent

from tools.billing_tools import check_balance, process_payment
from tools.network_tools import run_diagnostics, check_outage
from tools.escalation_tools import escalate_to_human

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")

# --------------------------------------------------
# App + ADK setup
# --------------------------------------------------
app = FastAPI(title="AI Voice Agent (Twilio + ADK)")
session_service = InMemorySessionService()

run_config = RunConfig(
    response_modalities=["text"]
)

# --------------------------------------------------
# Agent registry
# --------------------------------------------------
AGENTS = {
    "BillingAgent": billing_agent,
    "TechSupportAgent": tech_agent,
    "EscalationAgent": escalation_agent,
}

TOOLS = {
    "check_balance": check_balance,
    "process_payment": process_payment,
    "run_diagnostics": run_diagnostics,
    "check_outage": check_outage,
    "escalate_to_human": escalate_to_human,
}

# --------------------------------------------------
# Session Helper
# --------------------------------------------------
global USER_SESSION_MAP
if not "USER_SESSION_MAP" in globals():
    USER_SESSION_MAP = {}

async def get_or_create_session(user_id: str):
    session_id = USER_SESSION_MAP.get(user_id)
    session = None
    
    if session_id:
        try:
            session = await session_service.app_state.get_session(session_id)
        except Exception:
            pass
    
    if not session:
        session = await session_service.create_session(
            app_name="voice-agent",
            user_id=user_id
        )
        USER_SESSION_MAP[user_id] = session.id
    
    return session

def session_exists(user_id: str) -> bool:
    return user_id in USER_SESSION_MAP

# --------------------------------------------------
# CORE LOGIC (Shared between Twilio & Local)
# --------------------------------------------------
async def execute_agent_turn(user_text: str, session) -> str:
    """Run the ADK agent pipeline for a given user input and session."""
    try:
        # Step 1: Root Dispatcher
        root_ctx = InvocationContext(
            invocation_id=str(uuid.uuid4()),
            agent=root_agent,
            session=session,
            session_service=session_service,
            run_config=run_config
        )

        from google.adk.agents import Agent
        from agents.billing_agent import billing_agent as ba_proto
        from agents.tech_agent import tech_agent as ta_proto
        from agents.escalation_agent import escalation_agent as ea_proto
        
        # Instantiate fresh sub-agents
        billing_agent_new = Agent(name=ba_proto.name, instruction=ba_proto.instruction, model=ba_proto.model, tools=ba_proto.tools)
        tech_agent_new = Agent(name=ta_proto.name, instruction=ta_proto.instruction, model=ta_proto.model, tools=ta_proto.tools)
        escalation_agent_new = Agent(name=ea_proto.name, instruction=ea_proto.instruction, model=ea_proto.model, tools=ea_proto.tools)

        ephemeral_root = Agent(
            name="RootDispatcher",
            instruction=root_agent.instruction + f"\n\nUSER INPUT: {user_text}",
            model=root_agent.model,
            sub_agents=[billing_agent_new, tech_agent_new, escalation_agent_new]
        )

        selected_agent_name = None
        
        try:
            async for event in ephemeral_root.run_async(root_ctx):
                actions = getattr(event, "actions", None)
                if actions and actions.transfer_to_agent:
                    val = actions.transfer_to_agent
                    if isinstance(val, str):
                        selected_agent_name = val
                    else:
                        selected_agent_name = val.agent_name
                    logger.info("Routed to agent: %s", selected_agent_name)
                    break
        except Exception as e:
            logger.error("Root Agent Failed: %s", e)
            with open("error.log", "w") as f:
                import traceback
                f.write(traceback.format_exc())
            return "I am having trouble connecting to the service. Please try again later."

        agent = AGENTS.get(selected_agent_name)
        if not agent:
             return "Sorry, I could not understand your request."

        # Step 2: Selected Agent
        agent_ctx = InvocationContext(
            invocation_id=str(uuid.uuid4()),
            agent=agent,
            session=session,
            session_service=session_service,
            run_config=run_config
        )

        ephemeral_sub_agent = Agent(
            name=agent.name,
            instruction=agent.instruction + f"\n\nUSER INPUT: {user_text}",
            model=agent.model,
            tools=agent.tools
        )

        agent_reply = ""
        try:
            async for event in ephemeral_sub_agent.run_async(agent_ctx):
                content = getattr(event, "content", None)
                if not content or not content.parts:
                    continue
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        agent_reply += part.text.strip() + " "
                    if hasattr(part, "function_call") and part.function_call:
                        fn = part.function_call
                        tool = TOOLS.get(fn.name)
                        if tool:
                            try:
                                result = (
                                    await tool(**fn.args)
                                    if inspect.iscoroutinefunction(tool)
                                    else tool(**fn.args)
                                )
                                agent_reply += str(result) + " "
                            except Exception:
                                logger.exception("Tool execution failed")
                                agent_reply += "Sorry, there was an error. "
        except Exception as e:
             logger.error("Selected Agent Failed: %s", e)
             with open("error.log", "w") as f:
                import traceback
                f.write(traceback.format_exc())
             return "I am experiencing heavy traffic and cannot process your request right now."

        return agent_reply.strip()

    except Exception:
        import traceback
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
        return "Internal Error"

# --------------------------------------------------
# 1. TWILIO ENTRY POINT (Feedback & Routing)
# --------------------------------------------------
@app.api_route("/twilio/voice", methods=["GET", "POST"])
async def twilio_voice(request: Request):
    try:
        form = await request.form()
        user_text = form.get("SpeechResult")
        from_number = form.get("From", "anonymous")

        vr = VoiceResponse()

        # CASE A: User said something -> Acknowledge and Process
        if user_text:
            logger.info("User said: %s", user_text)
            
            # Intermediate Feedback
            vr.say("Got it. Kindly wait while I process your request.")
            
            # Redirect to processing endpoint
            params = urllib.parse.urlencode({
                "UserText": user_text,
                "From": from_number
            })
            vr.redirect(f"/twilio/process_agent?{params}", method="POST")
            return PlainTextResponse(str(vr), media_type="application/xml")

        # CASE B: Silence (No input)
        if session_exists(from_number):
            logger.info("Silence detected for existing session: %s", from_number)
            vr.say("I didn't hear anything. Are you still there?")
        else:
            logger.info("New call from: %s", from_number)
            vr.say("Hello. How can I help you today?")

        # Listen again
        gather = Gather(
            input="speech",
            action="/twilio/voice",
            method="POST",
            speech_timeout="auto",
            language="en-IN",
            timeout=4
        )
        vr.append(gather)
        return PlainTextResponse(str(vr), media_type="application/xml")

    except Exception:
        return PlainTextResponse("Internal Error", status_code=500)

# --------------------------------------------------
# 2. TWILIO AGENT PROCESSING
# --------------------------------------------------
@app.api_route("/twilio/process_agent", methods=["GET", "POST"])
async def process_agent(request: Request):
    try:
        params = request.query_params
        user_text = params.get("UserText")
        from_number = params.get("From", "anonymous")

        if not user_text:
            vr = VoiceResponse()
            vr.say("Sorry, I lost the connection.")
            return PlainTextResponse(str(vr), media_type="application/xml")

        # Create/Get ADK Session
        session = await get_or_create_session(from_number)
        
        # Execute Logic
        agent_reply = await execute_agent_turn(user_text, session)
        
        # Speak Answer + Listen Again
        vr = VoiceResponse()
        gather = Gather(
            input="speech",
            action="/twilio/voice", # Loop back to main endpoint
            method="POST",
            speech_timeout="auto",
            language="en-IN",
            timeout=4
        )
        gather.say(agent_reply or "Sorry, I missed that.")
        vr.append(gather)
        
        return PlainTextResponse(str(vr), media_type="application/xml")

    except Exception:
        return PlainTextResponse("Internal Error", status_code=500)

# --------------------------------------------------
# 3. LOCAL CHAT ENDPOINT (JSON)
# --------------------------------------------------
class ChatRequest(BaseModel):
    text: str
    user_id: str = "local_user"

@app.post("/local/chat")
async def local_chat(req: ChatRequest):
    try:
        logger.info("Local Chat: %s", req.text)
        session = await get_or_create_session(req.user_id)
        reply = await execute_agent_turn(req.text, session)
        return {"reply": reply}
    except Exception as e:
        logger.error("Local Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
