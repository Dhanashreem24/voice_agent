import os
from google.adk.agents import Agent
from prompts.system_prompts import ROOT_SYSTEM_PROMPT, TECH_PROMPT, BILLING_PROMPT, ESCALATION_PROMPT
from tools.billing_tools import check_balance, process_payment
from tools.network_tools import check_outage, run_diagnostics
from tools.escalation_tools import escalate_to_human
from agents.escalation_agent import escalation_agent # We can reuse this one if it has no tools/state, or recreate it.
# Actually, let's just recreate them all to be safe.

# Load Model Name
try:
    from dotenv import load_dotenv
    load_dotenv()
    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")
except ImportError:
    MODEL_NAME = "gemini-2.0-flash"

def create_agent_graph(user_id: str) -> Agent:
    """
    Creates a fresh Agent Graph for a specific request.
    Injects user_id into system prompts to ensure robust tool calling.
    """
    
    # helper to inject context
    def inject_id(prompt):
        return f"CURRENT USER ID: {user_id}\n\n{prompt}"

    # 1. Billing Agent
    billing = Agent(
        name="BillingAgent",
        instruction=inject_id(BILLING_PROMPT),
        model=MODEL_NAME,
        tools=[check_balance, process_payment]
    )

    # 2. Tech Support Agent
    tech = Agent(
        name="TechSupportAgent",
        instruction=inject_id(TECH_PROMPT),
        model=MODEL_NAME,
        tools=[check_outage, run_diagnostics]
    )
    
    # 3. Escalation Agent
    escalation = Agent(
        name="EscalationAgent",
        instruction=inject_id(ESCALATION_PROMPT),
        model=MODEL_NAME,
        tools=[escalate_to_human]
    )

    # 4. Root Dispatcher
    root = Agent(
        name="RootDispatcher",
        instruction=inject_id(ROOT_SYSTEM_PROMPT),
        model=MODEL_NAME,
        sub_agents=[tech, billing, escalation]
    )
    
    return root
