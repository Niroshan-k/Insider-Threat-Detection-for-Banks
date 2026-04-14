import pymongo
import random
from datetime import datetime, timedelta
import uuid
from faker import Faker

fake = Faker()

def generate_simulation_data():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["ndb_insider_threat"]

    print("🧹 Wiping database for a fresh simulation...")
    db.employees.delete_many({})
    db.customers.delete_many({})
    db.employee_actions.delete_many({})

    # --- 1. BUILD THE BANK (The Haystack) ---
    print("🏢 Hiring 20 random employees...")
    departments = ["TREASURY", "RETAIL_BANKING", "IT_OPS", "PAYMENTS_AND_SETTLEMENTS", "HR"]
    roles = ["OFFICER", "SENIOR_OFFICER", "MANAGER", "ASST_MANAGER"]
    
    employees = []
    # Create 19 normal employees
    for i in range(1, 20):
        employees.append({
            "employeeId": f"EMP_{1000+i}",
            "name": fake.name(),
            "department": random.choice(departments),
            "role": random.choice(roles),
            "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": random.randint(1, 10)}
        })
    
    # Add our NDB Suspects into the mix
    saman_id = "EMP_4821" # The bad actor
    kamal_id = "EMP_7721" # The victim of password theft
    employees.extend([
        {"employeeId": saman_id, "name": "Saman Perera", "department": "PAYMENTS_AND_SETTLEMENTS", "role": "ASST_MANAGER", "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": 2}},
        {"employeeId": kamal_id, "name": "Kamal Silva", "department": "PAYMENTS_AND_SETTLEMENTS", "role": "SENIOR_OFFICER", "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": 5}}
    ])
    db.employees.insert_many(employees)

    print("👥 Onboarding 500 normal customers...")
    base_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = base_time - timedelta(days=base_time.weekday() + 7) # Start from last Monday
    
    customers = []
    for i in range(500):
        customers.append({
            "customerId": f"CUST_{10000+i}",
            "name": fake.company() if random.random() > 0.5 else fake.name(),
            "createdAt": start_of_week - timedelta(days=random.randint(30, 3000)),
            "kycVerification": True
        })
    
    # Add the hidden ghost account (created just 2 days ago)
    ghost_id = "CUST_GHOST_01"
    customers.append({
        "customerId": ghost_id, "name": "Buy Today Holdings", 
        "createdAt": start_of_week + timedelta(days=4), # Created on Friday
        "kycVerification": False
    })
    db.customers.insert_many(customers)

    # --- 2. GENERATE 7 DAYS OF RANDOM NOISE ---
    print("⏳ Simulating 7 days of normal bank traffic (This might take a second)...")
    actions = []
    
    # Generate ~2000 normal actions scattered across the week
    for _ in range(2000):
        # 90% chance it happens during a weekday
        if random.random() < 0.90:
            random_day = start_of_week + timedelta(days=random.randint(0, 4)) # Mon-Fri
            random_time = random_day + timedelta(hours=random.randint(8, 16), minutes=random.randint(0, 59))
        else:
            # 10% chance it's weekend/after hours noise (False Positives to test your engine!)
            random_day = start_of_week + timedelta(days=random.randint(0, 6))
            random_time = random_day + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
        emp = random.choice(employees)
        action_type = random.choice(["CUSTOMER_QUERY", "ACCOUNT_VIEW", "LOGIN", "LOAN_APPROVAL", "ELECTRONIC_TRANSFER"])
        
        action = {
            "actionId": f"ACT_{uuid.uuid4().hex[:8]}",
            "employeeId": emp["employeeId"],
            "actionType": action_type,
            "timestamp": random_time,
            "location": {"ipAddress": fake.ipv4(), "branch": "Colombo_Main"}
        }

        # Add normal transaction details if needed
        if action_type in ["ELECTRONIC_TRANSFER", "LOAN_APPROVAL"]:
            cust = random.choice(customers[:-1]) # Don't accidentally use the ghost account
            action["relatedTransaction"] = {
                "transactionId": f"TXN_{uuid.uuid4().hex[:6]}",
                "amount": round(random.uniform(5000, 500000), 2), # Normal amounts
                "customerId": cust["customerId"],
                "beneficiary": {"name": fake.company()}
            }
        actions.append(action)

    # --- 3. INJECT THE NEEDLE (The NDB Fraud) ---
    print("💉 Injecting the NDB Rs. 13.2B fraud sequence into the timeline...")
    saturday_night = start_of_week + timedelta(days=5, hours=23, minutes=15) # Saturday 11:15 PM
    hacker_ip = "10.0.0.99"

    fraud_sequence = [
        # Saman logs in
        {"actionId": f"ACT_{uuid.uuid4().hex[:8]}", "employeeId": saman_id, "actionType": "LOGIN", "timestamp": saturday_night, "location": {"ipAddress": hacker_ip, "branch": "REMOTE_VPN"}},
        # Saman uses Kamal's stolen password from the SAME IP 2 mins later
        {"actionId": f"ACT_{uuid.uuid4().hex[:8]}", "employeeId": kamal_id, "actionType": "LOGIN", "timestamp": saturday_night + timedelta(minutes=2), "location": {"ipAddress": hacker_ip, "branch": "REMOTE_VPN"}},
        # Saman approves a massive loan to the unverified ghost account
        {"actionId": f"ACT_{uuid.uuid4().hex[:8]}", "employeeId": saman_id, "actionType": "LOAN_APPROVAL", "timestamp": saturday_night + timedelta(minutes=10), "location": {"ipAddress": hacker_ip, "branch": "REMOTE_VPN"},
         "relatedTransaction": {"transactionId": "TXN_LOAN_55", "amount": 50000000, "customerId": ghost_id}},
        # Saman wires the money out to buy crypto
        {"actionId": f"ACT_{uuid.uuid4().hex[:8]}", "employeeId": saman_id, "actionType": "ELECTRONIC_TRANSFER", "timestamp": saturday_night + timedelta(minutes=15), "location": {"ipAddress": hacker_ip, "branch": "REMOTE_VPN"},
         "relatedTransaction": {"transactionId": "TXN_CRYPTO_99", "amount": 15000000, "currency": "LKR", "beneficiary": {"name": "Buy Today Crypto Exchange", "accountNumber": "000999888"}}}
    ]
    actions.extend(fraud_sequence)

    # --- 4. SHUFFLE AND INSERT ---
    # Sort everything perfectly by time so the database looks totally natural
    actions.sort(key=lambda x: x["timestamp"])
    db.employee_actions.insert_many(actions)
    
    print(f"✅ Successfully created a realistic week of data with {len(actions)} total actions.")
    print("🔍 The haystack is built. Let's see if the engine can find the needle.")

if __name__ == "__main__":
    generate_simulation_data()