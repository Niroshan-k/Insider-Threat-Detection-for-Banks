import pymongo
import random
from datetime import datetime, timedelta, timezone
import uuid
from faker import Faker
from zoneinfo import ZoneInfo

fake = Faker()

def generate_simulation_data():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["ndb_insider_threat"]

    print("🧹 Wiping database for a fresh simulation...")
    db.employees.delete_many({})
    db.customers.delete_many({})
    db.employee_actions.delete_many({})

    # --- 1. BUILD THE BANK ---
    print("🏢 Hiring 20 random employees...")
    departments = ["TREASURY", "RETAIL_BANKING", "IT_OPS", "PAYMENTS_AND_SETTLEMENTS", "HR"]
    roles = ["OFFICER", "SENIOR_OFFICER", "MANAGER", "ASST_MANAGER"]
    
    employees = []
    for i in range(1, 20):
        employees.append({
            "employeeId": f"EMP_{1000+i}",
            "name": fake.name(),
            "department": random.choice(departments),
            "role": random.choice(roles),
            "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": random.randint(1, 10)}
        })
    
    saman_id = "EMP_4821" 
    kamal_id = "EMP_7721" 
    employees.extend([
        {"employeeId": saman_id, "name": "Saman Perera", "department": "PAYMENTS_AND_SETTLEMENTS", "role": "ASST_MANAGER", "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": 2}},
        {"employeeId": kamal_id, "name": "Kamal Silva", "department": "PAYMENTS_AND_SETTLEMENTS", "role": "SENIOR_OFFICER", "baseline": {"typicalWorkHours": {"start": 8, "end": 17}, "avgApprovalsPerDay": 5}}
    ])
    db.employees.insert_many(employees)

    print("👥 Onboarding 500 normal customers...")
    # FIX: Use Timezone Aware UTC and truncate to midnight to avoid adding hours on top of hours
    IST = ZoneInfo("Asia/Colombo")
    base_time = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = base_time - timedelta(days=base_time.weekday() + 7) 
    
    customers = []
    for i in range(500):
        customers.append({
            "customerId": f"CUST_{10000+i}",
            "name": fake.company() if random.random() > 0.5 else fake.name(),
            "createdAt": start_of_week - timedelta(days=random.randint(30, 3000)),
            "kycVerification": True
        })
    
    ghost_id = "CUST_GHOST_01"
    customers.append({
        "customerId": ghost_id, "name": "Buy Today Holdings", 
        "createdAt": start_of_week + timedelta(days=4), 
        "kycVerification": False
    })
    db.customers.insert_many(customers)

    # --- 2. GENERATE 7 DAYS OF RANDOM NOISE ---
    print("⏳ Simulating 7 days of normal bank traffic...")
    actions = []
    for _ in range(2000):
        # Always generate normal traffic: Weekdays (0-4) and Business Hours (8-16)
        random_day = start_of_week + timedelta(days=random.randint(0, 4)) 
        random_time = random_day + timedelta(hours=random.randint(8, 16), minutes=random.randint(0, 59))
        
        emp = random.choice(employees)
        action_type = random.choice(["CUSTOMER_QUERY", "ACCOUNT_VIEW", "LOGIN", "LOAN_APPROVAL", "ELECTRONIC_TRANSFER"])
        
        action = {
            "actionId": f"ACT_{uuid.uuid4().hex[:8]}",
            "employeeId": emp["employeeId"],
            "actionType": action_type,
            "timestamp": random_time,
            "location": {"ipAddress": fake.ipv4(), "branch": "Colombo_Main"}
        }

        if action_type in ["ELECTRONIC_TRANSFER", "LOAN_APPROVAL"]:
            cust = random.choice(customers[:-1]) 
            action["relatedTransaction"] = {
                "transactionId": f"TXN_{uuid.uuid4().hex[:6]}",
                "amount": round(random.uniform(5000, 500000), 2), 
                "customerId": cust["customerId"],
                "beneficiary": {"name": fake.company()}
            }
        actions.append(action)

    actions.sort(key=lambda x: x["timestamp"])
    db.employee_actions.insert_many(actions)
    
    print(f"✅ Successfully created a realistic week of data with {len(actions)} total actions.")

if __name__ == "__main__":
    generate_simulation_data()