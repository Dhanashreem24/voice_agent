import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-2.0-flash"

from google.adk.agents import Agent
from prompts.system_prompts import BILLING_PROMPT
from tools.billing_tools import check_balance, process_payment

billing_agent = Agent(
    name="BillingAgent",
    instruction=BILLING_PROMPT,
    model=MODEL_NAME,
    tools=[check_balance, process_payment]
)
