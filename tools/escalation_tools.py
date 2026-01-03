from datetime import datetime
from services.database import db

def escalate_to_human(user_id: str, reason: str) -> dict:
    """
    Escalates the call to a human agent by creating a support ticket.
    """
    if not user_id:
        return {"status": "error", "message": "No user ID provided"}

    ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    success = db.create_ticket(user_id, reason, ticket_id)
    
    if not success:
         return {"status": "error", "message": "Database error while creating ticket"}

    return {
        "action": "transfer_call",
        "queue": "Tier_2_Support",
        "user_id": user_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "wait_time": "2 minutes",
        "message": "I have escalated your request. A human agent will join shortly."
    }
