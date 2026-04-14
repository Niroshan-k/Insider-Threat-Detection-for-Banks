import streamlit as st
import pymongo
from datetime import datetime, timezone
import uuid
import time

st.set_page_config(page_title="Red Team Console", page_icon="💉")

@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://localhost:27017/")["ndb_insider_threat"]

db = init_connection()

st.title("💉 Cyber Warfare Console")
st.markdown("Inject highly coordinated attacks into the Live SOC Terminal.")

attack = st.radio("Select Vector:", [
    "A) NDB Crypto Heist (Credential Theft + Crypto Outflow)",
    "B) Ghost Account Heist (Credential Theft + Unverified Loan)"
])

if st.button("🔥 EXECUTE COMBO PAYLOAD", type="primary", use_container_width=True):
    # Fixed Deprecation Warning: Using timezone-aware UTC
    now = datetime.now(timezone.utc)
    
    # Generate unique identifiers so the engine's "Novelty Trap" works every time
    hacker_ip = f"10.99.{now.minute}.{now.second}" 
    unique_hash = uuid.uuid4().hex[:4]
    
    # STEP 1: The Setup (Simulate logging in as the victim to steal access)
    setup_payload = {
        "actionId": f"ACT_SETUP_{unique_hash}",
        "employeeId": "EMP_7721", # The Victim
        "actionType": "LOGIN",
        "timestamp": now,
        "location": {"ipAddress": hacker_ip, "branch": "VPN_ACCESS"}
    }
    db.employee_actions.insert_one(setup_payload)
    
    time.sleep(0.5) # Tiny delay for realism
    
    # STEP 2: The Strike (The actual attacker using the same stolen IP)
    if "Crypto" in attack:
        strike_payload = {
            "actionId": f"ACT_INJ_{unique_hash}",
            "employeeId": "EMP_4821", # The Attacker
            "actionType": "ELECTRONIC_TRANSFER",
            "timestamp": now,
            "location": {"ipAddress": hacker_ip, "branch": "VPN_ACCESS"},
            "relatedTransaction": {
                "amount": 25000000, 
                "beneficiary": {"name": f"Binance Exchange {unique_hash}"} # Unique Name!
            }
        }
    else:
        # Create the Ghost Customer in the DB first so the engine finds it
        ghost_id = f"CUST_GHOST_{unique_hash}"
        db.customers.insert_one({
            "customerId": ghost_id,
            "name": "Shell Corp Inc",
            "createdAt": now,
            "kycVerification": False
        })
        
        strike_payload = {
            "actionId": f"ACT_INJ_{unique_hash}",
            "employeeId": "EMP_4821", # The Attacker
            "actionType": "LOAN_APPROVAL",
            "timestamp": now,
            "location": {"ipAddress": hacker_ip, "branch": "VPN_ACCESS"},
            "relatedTransaction": {
                "amount": 50000000, 
                "customerId": ghost_id
            }
        }
        
    db.employee_actions.insert_one(strike_payload)
    st.success(f"[{now.strftime('%H:%M:%S')}] COMBO PAYLOAD DELIVERED. Check the main terminal.")