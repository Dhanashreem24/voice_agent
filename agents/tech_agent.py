import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-2.0-flash"

from google.adk.agents import Agent
from prompts.system_prompts import TECH_PROMPT
from tools.network_tools import run_diagnostics, check_outage

tech_agent = Agent(
    name="TechSupportAgent",
    instruction=TECH_PROMPT,
    model=MODEL_NAME,
    tools=[run_diagnostics, check_outage]
)
