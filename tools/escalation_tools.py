def escalate_to_human(reason: str):
    return {
        "escalated": True,
        "queue": "Human Support",
        "reason": reason
    }
