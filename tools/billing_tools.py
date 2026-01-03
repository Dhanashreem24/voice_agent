from datetime import date, timedelta
from services.database import db
from uuid import uuid4

def generate_txn_id():
    return f"TXN-{uuid4().hex[:8].upper()}"

def check_balance(user_id: str) -> dict:
    if not user_id:
        return {"status": "error", "message": "No user ID provided"}
        
    user = db.get_user(user_id)

    if not user:
        return {"status": "error", "message": "User not found in database"}

    return {
        "status": "success",
        "customer_name": user.get("name", "Customer"),
        "balance_amount": user.get("balance", 0.0),
        "currency": "INR",
        "due_date": (date.today() + timedelta(days=7)).isoformat()
    }

def process_payment(user_id: str, amount: float) -> dict:
    if not user_id:
        return {"status": "error", "message": "No user ID provided"}

    if amount <= 0:
        return {"status": "error", "message": "Invalid amount"}

    new_balance = db.update_balance(user_id, amount)
    if new_balance is None:
        return {"status": "error", "message": "User not found"}

    return {
        "status": "success",
        "amount_paid": amount,
        "remaining_balance": new_balance,
        "transaction_id": generate_txn_id()
    }
