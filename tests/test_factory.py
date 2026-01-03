import pytest
from agents.agent_factory import create_agent_graph

def test_agent_creation():
    user_id = "+918275267982"
    root_agent = create_agent_graph(user_id)
    
    assert root_agent.name == "RootDispatcher"
    # Check if User ID is injected into instructions
    assert f"CURRENT USER ID: {user_id}" in root_agent.instruction
    
    # Check sub-agents
    sub_agents = {agent.name: agent for agent in root_agent.sub_agents}
    assert "BillingAgent" in sub_agents
    assert "TechSupportAgent" in sub_agents
    assert "EscalationAgent" in sub_agents
    
    # Check Sub-Agent Prompt Injection
    assert f"CURRENT USER ID: {user_id}" in sub_agents["BillingAgent"].instruction
