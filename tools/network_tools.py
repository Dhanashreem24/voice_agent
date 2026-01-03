import random
from services.database import db

def check_outage(user_id: str) -> dict:
    print(f"DEBUG: check_outage called with user_id={user_id}")
    if not user_id:
        return {"status": "error", "message": "No user ID provided"}
        
    user = db.get_user(user_id)
    if not user:
        return {"status": "error", "message": "User not found"}

    region = user.get("region", "Unknown")
    status = db.get_network_status(region)

    if status == "Outage Detected":
        return {
            "status": "outage_confirmed",
            "region": region,
            "estimated_resolution": "90 minutes",
            "message": "There is a known outage in your area."
        }

    return {
        "status": "operational",
        "region": region,
        "message": "No known outages in your area."
    }

def run_diagnostics(user_id: str) -> dict:
    if not user_id:
        return {"status": "error", "message": "No user ID provided"}
        
    user = db.get_user(user_id)
    if not user:
        return {"status": "error", "message": "User not found"}

    # Simulate random diagnostics
    health = random.choices(
        ["healthy", "packet_loss"],
        weights=[0.8, 0.2]
    )[0]

    router_id = user.get("router_id", "Unknown-Router")

    if health == "healthy":
        return {
            "device": router_id,
            "status": "Online",
            "latency": "10ms",
            "packet_loss": "0%",
            "recommendation": "Please restart your router."
        }

    return {
        "device": router_id,
        "status": "Unstable",
        "issue": "Packet Loss",
        "recommendation": "Escalating for line reset."
    }
