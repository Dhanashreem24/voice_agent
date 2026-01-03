from services.database import db

def seed():
    print("Seeding database...")
    
    # Also valid for "local_tester"
    
    # 1. Seed Main User
    user_id = "+911234567890"
    user_data = {
        "name": "Lucifer Morningstar",
        "balance": 1245.0,
        "region": "India-West",
        "router_id": "CISCO-X99"
    }
    db.client.set(f"user:{user_id}", str(user_data).replace("'", '"')) # Simple JSON hack or import json
    # Better: use json
    import json
    db.client.set(f"user:{user_id}", json.dumps(user_data))
    print(f"User {user_id} seeded.")
    
    # 2. Seed Local Tester
    user_id_local = "local_tester"
    db.client.set(f"user:{user_id_local}", json.dumps(user_data))
    print(f"User {user_id_local} seeded.")

    # 3. Network Status
    db.set_network_status("India-West", "Operational")
    db.set_network_status("India-South", "Outage Detected")
    print("Network status seeded.")
    
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
