import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-2.0-flash"

from google.adk.agents import Agent
from prompts.system_prompts import ROOT_SYSTEM_PROMPT
from agents.tech_agent import tech_agent
from agents.billing_agent import billing_agent
from agents.escalation_agent import escalation_agent

root_agent = Agent(
    name="RootDispatcher",
    instruction=ROOT_SYSTEM_PROMPT,
    model=MODEL_NAME,
    sub_agents=[
        tech_agent,
        billing_agent,
        escalation_agent
    ]
)
