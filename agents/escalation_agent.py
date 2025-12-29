import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-2.0-flash"

from google.adk.agents import Agent
from prompts.system_prompts import ESCALATION_PROMPT
from tools.escalation_tools import escalate_to_human

escalation_agent = Agent(
    name="EscalationAgent",
    instruction=ESCALATION_PROMPT,
    model=MODEL_NAME,
    tools=[escalate_to_human]
)
