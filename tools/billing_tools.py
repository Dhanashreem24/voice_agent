def check_balance(user_id: str = "user_001"):
    return "Your current balance is ₹1,245. Thank you for asking."
    return {
        "user_id": user_id,
        "balance": "₹1,245",
        "currency": "INR"
    }

def process_payment(amount: str):
    return {
        "status": "success",
        "amount": amount,
        "message": "Payment processed successfully"
    }
