import os
import json
import redis
import time
from dotenv import load_dotenv

load_dotenv()

class RedisDatabase:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            self.client.ping() # Check connection
            print(f"Connected to Redis at {redis_url}")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            self.client = None

    def get_user(self, user_id: str):
        if not self.client: return None
        data = self.client.get(f"user:{user_id}")
        return json.loads(data) if data else None

    def update_balance(self, user_id: str, amount_paid: float):
        """Atomically updates user balance."""
        if not self.client: return None
        
        key = f"user:{user_id}"
        
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    data = pipe.get(key)
                    if not data:
                        return None
                    
                    user = json.loads(data)
                    current_balance = float(user.get("balance", 0))
                    new_balance = max(0, current_balance - amount_paid)
                    user["balance"] = new_balance
                    
                    pipe.multi()
                    pipe.set(key, json.dumps(user))
                    pipe.execute()
                    return new_balance
                except redis.WatchError:
                    continue # Retry on conflict

    def set_network_status(self, region: str, status: str):
        if not self.client: return None
        self.client.set(f"network:{region}", status)

    def get_network_status(self, region: str):
        if not self.client: return "Unknown"
        return self.client.get(f"network:{region}") or "Unknown"

    def create_ticket(self, user_id: str, reason: str, ticket_id: str):
        """Creates a support ticket in Redis."""
        if not self.client: return False
        
        ticket_data = {
            "ticket_id": ticket_id,
            "user_id": user_id,
            "reason": reason,
            "status": "OPEN",
            "created_at": time.time()
        }
        
        # Store ticket details
        self.client.set(f"ticket:{ticket_id}", json.dumps(ticket_data))
        
        # Add to global list of open tickets
        self.client.rpush("tickets:open", ticket_id)
        
        # Add to user's ticket list
        self.client.rpush(f"tickets:user:{user_id}", ticket_id)
        
        return True

# Global DB Instance
db = RedisDatabase()
