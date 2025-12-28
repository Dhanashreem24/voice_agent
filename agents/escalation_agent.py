import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-1.5-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-1.5-flash"

from google.adk.agents import Agent, LlmAgent
from prompts.system_prompts import ESCALATION_PROMPT
from tools.escalation_tools import escalate_to_human

escalation_agent = LlmAgent(
    name="EscalationAgent",
    instruction=ESCALATION_PROMPT,
    model=MODEL_NAME,
    tools=[escalate_to_human]
)