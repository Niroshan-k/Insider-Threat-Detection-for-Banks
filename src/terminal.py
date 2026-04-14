import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime
import time
import sys
import os
import plotly.express as px

# Ensure Python can find our engine module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from src.engine.rules import evaluate_employee_action
except ModuleNotFoundError:
    st.error("⚠️ Could not import rules.py.")

# --- TERMINAL STYLING (Bloomberg Vibe) ---
st.set_page_config(page_title="NDB SOC Terminal", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Extreme Dark Mode */
    .stApp { background-color: #050505; color: #e0e0e0; }
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
    
    /* Global Monospace Font */
    * { font-family: 'Courier New', Courier, monospace !important; }
    
    /* Terminal Dataframes */
    [data-testid="stDataFrame"] { background-color: #0a0a0a; }
    
    /* Bloomberg Orange Headers */
    h1, h2, h3, h4 { color: #ff9900 !important; margin-bottom: 0px !important; padding-bottom: 2px !important; }
    
    /* Style the bordered containers to look like terminal screens */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #333333 !important;
        background-color: #0a0a0a !important;
        border-radius: 0px !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://localhost:27017/")["ndb_insider_threat"]

db = init_connection()

st.title("SYS.TERMINAL // NDB INSIDER THREAT OPS")
st.caption(f"LIVE FEED ACTIVE | SYS.TIME: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | CBSL COMPLIANT")

# --- FETCH & SCORE DATA ---
# Increased limit to 150 so alerts stay on screen longer
recent_actions = list(db.employee_actions.find().sort("timestamp", -1).limit(150))
scored_data, alerts = [], []

for action in recent_actions:
    score = evaluate_employee_action(action, db)
    row = {
        "TIME": action.get("timestamp"),
        "EMP_ID": action.get("employeeId"),
        "TYPE": action.get("actionType"),
        "IP": action.get("location", {}).get("ipAddress", "N/A"),
        "RISK": score["riskScore"],
        "STATUS": "BLOCKED" if score["isAlert"] else "NORMAL"
    }
    scored_data.append(row)
    if score["isAlert"]:
        alerts.append({"TIME": action.get("timestamp").strftime("%H:%M:%S"), "EMP_ID": row["EMP_ID"], "FLAGS": ", ".join(score["anomalyFlags"])})

df = pd.DataFrame(scored_data)

# --- TOP ROW: METRICS PANELS ---
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("DB.LATENCY", "1.1ms", "-0.2ms")
    m2.metric("MSG.RATE", "Active", "OK")
    m3.metric("EVENTS.IN.MEMORY", str(len(df)), "OK")
    m4.metric("CRITICAL.ALERTS", str(len(alerts)), f"+{len(alerts)}" if alerts else "0", delta_color="inverse")

# --- MIDDLE ROW: CHARTS ---
col_main_chart, col_side_chart = st.columns([7, 3])

with col_main_chart:
    with st.container(border=True):
        st.subheader("▶ RISK VOLATILITY (TRADING VIEW)")
        if not df.empty:
            # FIX: Create a string version of the time for categorical X-axis
            df['CHART_TIME'] = df['TIME'].dt.strftime("%H:%M:%S")
            
            # Replaced x="TIME" with x="CHART_TIME"
            fig_bar = px.bar(
                df, x="CHART_TIME", y="RISK", color="STATUS",
                color_discrete_map={"NORMAL": "#00cc66", "BLOCKED": "#ff3333"},
                template="plotly_dark", height=280
            )
            fig_bar.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), 
                plot_bgcolor="#0a0a0a", paper_bgcolor="#0a0a0a",
                bargap=0.1 # Tightly packed bars
            )
            fig_bar.add_hline(y=0.75, line_dash="dash", line_color="#ff9900", annotation_text="CBSL ALERT LIMIT (0.75)")
            
            # Force the X-axis to treat time as distinct categories, not a continuous timeline
            fig_bar.update_xaxes(title_text="", showgrid=False, type='category')
            fig_bar.update_yaxes(title_text="RISK SCORE", showgrid=True, gridcolor="#222", range=[0, 1.1])
            
            st.plotly_chart(fig_bar, use_container_width=True)

with col_side_chart:
    with st.container(border=True):
        st.subheader("▶ EVENT DISTRIBUTION")
        if not df.empty:
            # Added a Donut Chart for situational awareness
            action_counts = df['TYPE'].value_counts().reset_index()
            action_counts.columns = ['TYPE', 'COUNT']
            fig_pie = px.pie(
                action_counts, values='COUNT', names='TYPE', hole=0.6,
                template="plotly_dark", height=280
            )
            fig_pie.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="#0a0a0a", paper_bgcolor="#0a0a0a",
                showlegend=False
            )
            fig_pie.update_traces(textposition='inside', textinfo='label+percent')
            st.plotly_chart(fig_pie, use_container_width=True)

# --- BOTTOM ROW: TERMINAL FEEDS ---
col_feed, col_alerts = st.columns([7, 3])

with col_feed:
    with st.container(border=True):
        st.subheader("▶ RAW TRANSACTION STREAM")
        df['TIME'] = df['TIME'].dt.strftime("%H:%M:%S")
        def highlight_terminal(row):
            if row['STATUS'] == 'BLOCKED': return ['background-color: #4a0000; color: #ff4444; font-weight: bold'] * len(row)
            return ['color: #00cc66'] * len(row)

        if not df.empty:
            st.dataframe(df.style.apply(highlight_terminal, axis=1), use_container_width=True, height=300)

with col_alerts:
    with st.container(border=True):
        st.subheader("▶ CRITICAL ALERT LOG")
        if alerts:
            for alert in alerts[:6]: # Show top 6
                st.error(f"[{alert['TIME']}] {alert['EMP_ID']}\n\n>> {alert['FLAGS']}")
        else:
            st.success(">> NO CRITICAL ALERTS DETECTED.")

# The heartbeat
time.sleep(2)
st.rerun()