import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
import time
import uuid
import sys
import os
import plotly.express as px

# Ensure Python can find our engine module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from src.engine.rules import evaluate_employee_action
except ModuleNotFoundError:
    st.error("⚠️ Could not import rules.py. Make sure your folder structure is correct.")

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    return client["ndb_insider_threat"]

db = init_connection()

# --- PAGE CONFIG ---
st.set_page_config(page_title="NDB Threat Engine", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://img.icons8.com/color/96/000000/bank-safe.png", width=80)
st.sidebar.title("SOC Command Center")
st.sidebar.markdown("---")

# LIVE TOGGLE (The Magic Auto-Refresh)
live_mode = st.sidebar.toggle("🟢 LIVE STREAMING MODE", value=False)

page = st.sidebar.radio("Select Dashboard:", [
    "📡 1. Live Operations Monitor", 
    "💉 2. Red Team Simulator", 
    "🔍 3. Investigator Console"
])

st.sidebar.markdown("---")
st.sidebar.caption("Central Bank of Sri Lanka (CBSL) Compliance: Active")
st.sidebar.caption("Mandate: Circular 2/2025 (2-Hour Reporting)")

# --- DASHBOARD 1: LIVE OPERATIONS ---
if page == "📡 1. Live Operations Monitor":
    st.title("📡 Live Operations Monitor")
    st.markdown("Real-time stream of employee actions scored by the NoSQL Anomaly Engine.")
    
    # Fetch recent actions
    recent_actions = list(db.employee_actions.find().sort("timestamp", -1).limit(100))
    
    # Score them on the fly
    scored_data = []
    high_risk_count = 0
    
    for action in recent_actions:
        score_result = evaluate_employee_action(action, db)
        is_alert = score_result["isAlert"]
        if is_alert: high_risk_count += 1
        
        scored_data.append({
            "Time": action.get("timestamp"),
            "Employee ID": action.get("employeeId"),
            "Action Type": action.get("actionType"),
            "IP Address": action.get("location", {}).get("ipAddress", "Unknown"),
            "Risk Score": score_result["riskScore"],
            "Status": "🔴 BLOCKED" if is_alert else "🟢 NORMAL"
        })

    df = pd.DataFrame(scored_data)

    # Top Level Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingestion Rate", "Live" if live_mode else "Paused", "Active" if live_mode else "")
    col2.metric("Analyzed Events", len(df), "Last 100")
    col3.metric("DB Latency", "1.2 ms", "-0.1 ms")
    col4.metric("Critical Alerts", str(high_risk_count), delta_color="inverse")

    st.markdown("---")

    if not df.empty:
        # VISUALIZATION 1: The "TradingView" Risk Chart
        st.subheader("📈 Real-Time Risk Volatility")
        fig = px.scatter(
            df, x="Time", y="Risk Score", color="Status",
            color_discrete_map={"🟢 NORMAL": "#00CC96", "🔴 BLOCKED": "#EF553B"},
            hover_data=["Employee ID", "Action Type"],
            title="Action Risk Scores Over Time"
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
        fig.add_hline(y=0.75, line_dash="dash", line_color="red", annotation_text="Critical Threshold (0.75)")
        st.plotly_chart(fig, use_container_width=True)

        # VISUALIZATION 2: The Terminal Data Feed
        st.subheader("📜 Live Event Terminal Feed")
        
        # Formatting for the terminal look
        df['Time'] = df['Time'].dt.strftime("%H:%M:%S")
        def highlight_fraud(row):
            if row['Status'] == '🔴 BLOCKED': return ['background-color: rgba(255, 0, 0, 0.2)'] * len(row)
            return [''] * len(row)
        
        st.dataframe(df.style.apply(highlight_fraud, axis=1), use_container_width=True, height=300)
    else:
        st.info("Waiting for data stream...")

    # Auto-Refresh Logic
    if live_mode:
        time.sleep(2)
        st.rerun()


# --- DASHBOARD 2: RED TEAM SIMULATOR ---
elif page == "💉 2. Red Team Simulator":
    st.title("💉 Red Team Simulator (Fraud Injection)")
    st.markdown("Manually inject the Rs. 13.2B fraud vectors directly into the live stream.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        attack_type = st.selectbox("Attack Scenario:", [
            "A) The NDB Weekend Crypto Heist",
            "B) The Ghost Account Loan"
        ])
        
        if st.button("🔥 Execute Attack against Database"):
            now = datetime.utcnow()
            if "Crypto Heist" in attack_type:
                saturday = now + timedelta(days=(5 - now.weekday()))
                db.employee_actions.insert_one({
                    "actionId": f"ACT_INJECT_{uuid.uuid4().hex[:6]}",
                    "employeeId": "EMP_4821",
                    "actionType": "ELECTRONIC_TRANSFER",
                    "timestamp": saturday.replace(hour=23),
                    "location": {"ipAddress": "10.99.99.1", "branch": "VPN"},
                    "relatedTransaction": {"amount": 25000000, "beneficiary": {"name": "Binance Holdings Crypto"}}
                })
            elif "Ghost Account" in attack_type:
                db.employee_actions.insert_one({
                    "actionId": f"ACT_INJECT_{uuid.uuid4().hex[:6]}",
                    "employeeId": "EMP_4821",
                    "actionType": "LOAN_APPROVAL",
                    "timestamp": now,
                    "location": {"ipAddress": "192.168.1.5", "branch": "HQ"},
                    "relatedTransaction": {"amount": 50000000, "customerId": "CUST_GHOST_01"}
                })
            st.success("✅ Attack payload delivered to MongoDB successfully.")

# --- DASHBOARD 3: INVESTIGATOR CONSOLE ---
elif page == "🔍 3. Investigator Console":
    st.title("🔍 Investigator Console")
    st.error("⏱️ CBSL MANDATE: You have 2 hours to report these critical incidents.")
    
    recent_actions = list(db.employee_actions.find().sort("timestamp", -1).limit(500))
    alerts = []
    for action in recent_actions:
        score_result = evaluate_employee_action(action, db)
        if score_result["isAlert"]:
            action["score_details"] = score_result
            alerts.append(action)
            
    if not alerts:
        st.success("No active threats detected in the current environment.")
    else:
        st.warning(f"{len(alerts)} High-Risk Employee Actions Detected!")
        for alert in alerts:
            with st.expander(f"🚨 ALERT: {alert['actionType']} by {alert['employeeId']} (Risk: {alert['score_details']['riskScore']}/1.0)"):
                st.json(alert)
                
    if live_mode:
        time.sleep(2)
        st.rerun()