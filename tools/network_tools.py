def run_diagnostics():
    return {
        "status": "Router reachable",
        "signal_strength": "Strong",
        "packet_loss": "0%"
    }

def check_outage(location: str = "default"):
    return {
        "outage": False,
        "location": location,
        "message": "No outage detected"
    }
