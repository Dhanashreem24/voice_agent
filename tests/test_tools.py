import pytest
from unittest.mock import MagicMock, patch
from tools.billing_tools import check_balance, process_payment
from tools.network_tools import check_outage, run_diagnostics
from tools.escalation_tools import escalate_to_human

# Mock Database
@pytest.fixture
def mock_db():
    with patch('tools.billing_tools.db') as mock_billing, \
         patch('tools.network_tools.db') as mock_network, \
         patch('tools.escalation_tools.db') as mock_escalation:
        yield {
            "billing": mock_billing,
            "network": mock_network,
            "escalation": mock_escalation
        }

def test_check_balance_success(mock_db):
    mock_db["billing"].get_user.return_value = {"balance": 500.0}
    result = check_balance("user123")
    assert result["status"] == "success"
    assert result["balance_amount"] == 500.0

def test_check_balance_no_user():
    result = check_balance("")
    assert result["status"] == "error"

def test_check_outage_found(mock_db):
    mock_db["network"].get_user.return_value = {"region": "India-West"}
    mock_db["network"].get_network_status.return_value = "Outage Detected"
    
    result = check_outage("user123")
    assert result["status"] == "outage_confirmed"
    assert "known outage" in result["message"]

def test_escalation_ticket(mock_db):
    mock_db["escalation"].create_ticket.return_value = True
    
    result = escalate_to_human("user123", "I am angry")
    assert result["action"] == "transfer_call"
    assert "TICKET-" in result["ticket_id"]
    assert result["user_id"] == "user123"
