import pymongo
import time
import random
import uuid
from datetime import datetime, timezone, timedelta

def pump_live_data():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["ndb_insider_threat"]
    
    print("📡 LIVE DATA PUMPER ACTIVATED")
    
    # 1. Pull employees
    employees = list(db.employees.find({}, {"employeeId": 1, "_id": 0}))
    emp_ids = [e["employeeId"] for e in employees]
    
    # 2. Pull safe, KYC-verified customers
    customers = list(db.customers.find({"kycVerification": True}, {"customerId": 1, "_id": 0}))
    cust_ids = [c["customerId"] for c in customers]
    
    if not emp_ids or not cust_ids:
        print("❌ Error: No valid employees or customers found!")
        return

    print(f"✅ Loaded {len(emp_ids)} Employees and {len(cust_ids)} Normal Customers.")
    
    actions = ["CUSTOMER_QUERY", "ACCOUNT_VIEW", "LOGIN", "LOAN_APPROVAL", "ELECTRONIC_TRANSFER"]
    safe_vendors = ["SLT Telecom", "CEB Power", "Water Board", "Dialog Axiata", "Office Supplies Co"]

    try:
        while True:
            # FIX: Shift UTC to Sri Lanka Standard Time (+5:30) so the engine knows it's daytime!
            now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            
            action_type = random.choice(actions)
            emp_id = random.choice(emp_ids)
            
            # Static, safe IP to prevent accidental credential abuse flags
            safe_ip = f"192.168.1.{100 + emp_ids.index(emp_id)}"
            
            action = {
                "actionId": f"ACT_LIVE_{uuid.uuid4().hex[:6]}",
                "employeeId": emp_id,
                "actionType": action_type,
                "timestamp": now,
                "location": {"ipAddress": safe_ip, "branch": "Colombo_Main"}
            }
            
            # Safe amounts and approved vendors
            if action_type in ["ELECTRONIC_TRANSFER", "LOAN_APPROVAL"]:
                
                # 80% of the time, use a known vendor. 
                # 20% of the time, create a BRAND NEW vendor to trigger a "Yellow Flag" (+0.4 Risk)
                if random.random() < 0.80:
                    chosen_vendor = random.choice(safe_vendors)
                else:
                    chosen_vendor = f"Local_Supplier_{random.randint(1000, 9999)} Ltd"

                action["relatedTransaction"] = {
                    "transactionId": f"TXN_{uuid.uuid4().hex[:6]}",
                    "amount": round(random.uniform(5000, 500000), 2), 
                    "customerId": random.choice(cust_ids), 
                    "beneficiary": {"name": chosen_vendor}
                }
            
            db.employee_actions.insert_one(action)
            print(f"[{now.strftime('%H:%M:%S')}] Safe {action_type} executed by {emp_id}")
            
            time.sleep(random.uniform(1.0, 3.0))
            
    except KeyboardInterrupt:
        print("\n⏹️ Live stream stopped.")

if __name__ == "__main__":
    pump_live_data()