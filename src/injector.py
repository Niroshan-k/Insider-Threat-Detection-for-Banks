import streamlit as st
import pymongo
from datetime import datetime, timezone, timedelta
import uuid
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Red Team Console", page_icon="💉", layout="wide")

# --- TERMINAL CSS (HACKER MODE) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00FF41; }
    .block-container { padding: 1rem 2rem; max-width: 100%; }
    * { font-family: 'Courier New', monospace !important; letter-spacing: 0.5px; border-radius: 0px !important; }
    h1, h2, h3 { color: #FF3333 !important; font-weight: bold; } /* Red headers for the attack console */
    
    /* Panels */
    [data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid #330000; background-color: #050000; padding: 10px; }
    
    /* Hide Streamlit junk */
    header {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://localhost:27017/")["ndb_insider_threat"]

db = init_connection()

# --- HEADER ---
st.markdown("## 🔴 RED_TEAM :: ATTACK_VECTOR_CONSOLE")
now_str = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"SYS_TIME::{now_str} LKT | AUTHORIZATION::OVERRIDE")

# --- ATTACK CONFIGURATION ---
with st.container(border=True):
    st.markdown("### 01::SELECT_PAYLOAD")
    attack = st.radio("TARGET_VULNERABILITY:", [
        "VECTOR_ALPHA: NDB Crypto Heist (Credential Theft + Crypto Outflow)",
        "VECTOR_BETA: Ghost Account Heist (Credential Theft + Unverified Loan)"
    ])

    execute = st.button("🔥 EXECUTE_COMBO_STRIKE", type="primary", use_container_width=True)

# --- EXECUTION LOGIC & UI ---
if execute:
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    hacker_ip = f"10.99.{now.minute}.{now.second}" 
    unique_hash = uuid.uuid4().hex[:4]
    
    with st.spinner("Injecting payload into core database..."):
        time.sleep(0.5) # Theatrical delay
        
        # STEP 1: The Setup
        setup_payload = {
            "actionId": f"ACT_SETUP_{unique_hash}",
            "employeeId": "EMP_7721", # The Victim
            "actionType": "LOGIN",
            "timestamp": now,
            "location": {"ipAddress": hacker_ip, "branch": "VPN_ACCESS"}
        }
        db.employee_actions.insert_one(setup_payload)
        
        # STEP 2: The Strike
        if "Crypto" in attack:
            strike_payload = {
                "actionId": f"ACT_INJ_{unique_hash}",
                "employeeId": "EMP_4821", # The Attacker
                "actionType": "ELECTRONIC_TRANSFER",
                "timestamp": now,
                "location": {"ipAddress": hacker_ip, "branch": "VPN_ACCESS"},
                "relatedTransaction": {
                    "amount": 25000000, 
                    "beneficiary": {"name": f"Binance Exchange {unique_hash}"}
                }
            }
        else:
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

    # --- SHOW THE RESULTS TO THE EXAMINER ---
    with st.container(border=True):
        st.markdown("### 02::PAYLOAD_DELIVERY_LOG")
        st.success(f">> STATUS: BREACH SUCCESSFUL AT {now.strftime('%H:%M:%S')}")
        
        col_setup, col_strike = st.columns(2)
        
        with col_setup:
            st.markdown("**[PHASE 1] CREDENTIAL COMPROMISE:**")
            st.caption("Logging in as victim from unauthorized IP.")
            st.json(setup_payload)
            
        with col_strike:
            st.markdown("**[PHASE 2] FRAUD EXECUTION:**")
            st.caption("Executing high-risk transaction from identical IP.")
            st.json(strike_payload)
            
        st.info("👉 Check the SOC Terminal. The engine should have linked these two events instantly.")