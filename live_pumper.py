import pymongo
import time
import random
import uuid
from datetime import datetime

def pump_live_data():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["ndb_insider_threat"]
    
    print("📡 LIVE DATA PUMPER ACTIVATED")
    print("Streaming normal transactions to MongoDB... (Press Ctrl+C to stop)")
    
    employees = ["EMP_4821", "EMP_7721", "EMP_1001", "EMP_1002", "EMP_1003"]
    actions = ["CUSTOMER_QUERY", "ACCOUNT_VIEW", "LOGIN"]
    
    try:
        while True:
            # Create a normal action happening RIGHT NOW
            action = {
                "actionId": f"ACT_LIVE_{uuid.uuid4().hex[:6]}",
                "employeeId": random.choice(employees),
                "actionType": random.choice(actions),
                "timestamp": datetime.utcnow(),
                "location": {"ipAddress": f"192.168.1.{random.randint(10, 99)}", "branch": "Colombo_Main"}
            }
            
            db.employee_actions.insert_one(action)
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Inserted normal action for {action['employeeId']}")
            
            # Wait 1 to 3 seconds before the next event
            time.sleep(random.uniform(1.0, 3.0))
            
    except KeyboardInterrupt:
        print("\n⏹️ Live stream stopped.")

if __name__ == "__main__":
    pump_live_data()