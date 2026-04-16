import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timezone
import time
import sys
import os
import plotly.express as px

# --- IMPORT ENGINE ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from src.engine.rules import evaluate_employee_action
except ModuleNotFoundError:
    st.error("⚠️ rules.py not found")

# --- PAGE CONFIG ---
st.set_page_config(page_title="NDB SOC Terminal", layout="wide")

# --- TERMINAL CSS (HARDCORE MODE) ---
st.markdown("""
<style>
    .stApp {
        background-color: #000000;
        color: #00FF41;
    }

    .block-container {
        padding: 0.2rem 0.5rem;
        max-width: 100%;
    }

    * {
        font-family: 'Courier New', monospace !important;
        letter-spacing: 0.5px;
        border-radius: 0px !important;
    }

    h1, h2, h3 {
        color: #FF9900 !important;
        font-weight: bold;
    }

    /* Panels */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #222;
        background-color: #050505;
        padding: 4px;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        background-color: #000000;
        border: 1px solid #111;
    }
            
    /* Hide Streamlit top bar completely */
    header {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}

    /* Remove top spacing */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0.2rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://localhost:27017/")["ndb_insider_threat"]

db = init_connection()

# --- HEADER ---
st.markdown("## TERMINAL")
now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"SYSTEM_TIME::{now_utc} UTC | STATUS::ACTIVE")

# --- FETCH DATA ---
recent_actions = list(db.employee_actions.find().sort("timestamp", -1).limit(150))

scored_data = []
alerts = []

for action in recent_actions:
    score = evaluate_employee_action(action, db)
    risk_val = score["riskScore"]

    # FIX: 3-Tier Risk Logic
    if score["isAlert"]:
        status_label = "BLOCKED"
    elif risk_val > 0.5:
        status_label = "WARNING"
    else:
        status_label = "NORMAL"

    row = {
        "TIME": action.get("timestamp"),
        "EMP": action.get("employeeId"),
        "TYPE": action.get("actionType"),
        "IP": action.get("location", {}).get("ipAddress", "N/A"),
        "RISK": risk_val,
        "STATUS": status_label
    }

    scored_data.append(row)

    if score["isAlert"]:
        alerts.append({
            "TIME": action.get("timestamp").strftime("%H:%M:%S"),
            "EMP": row["EMP"],
            "FLAGS": ", ".join(score["anomalyFlags"])
        })

df = pd.DataFrame(scored_data)

# --- METRICS ---
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("DB_LATENCY", "1.1ms")
    m2.metric("STREAM_STATUS", "ACTIVE")
    m3.metric("EVENT_BUFFER", str(len(df)))
    m4.metric("ALERT_COUNT", str(len(alerts)))

# --- CHARTS ---
col1, col2 = st.columns([7, 3])

with col1:
    with st.container(border=True):
        st.markdown("### RISK_STREAM::VOLATILITY_INDEX")

        if not df.empty:
            df['TIME'] = pd.to_datetime(df['TIME'], utc=True)
            df_chart = df.iloc[::-1].copy()

            df_chart['CHART_TIME'] = df_chart['TIME'].dt.strftime("%H:%M:%S.%f").str[:-4]

            fig = px.bar(
                df_chart,
                x="CHART_TIME",
                y="RISK",
                color="STATUS",
                # FIX: Added the YELLOW color mapping for the WARNING tier
                color_discrete_map={
                    "NORMAL": "#00FF41",
                    "WARNING": "#FFD700", 
                    "BLOCKED": "#FF3333"
                },
                template="plotly_dark",
                height=260
            )

            fig.update_layout(
                barmode="overlay",
                showlegend=False,
                font=dict(size=10, color="#00FF41"),
                margin=dict(l=0, r=0, t=5, b=0),
                plot_bgcolor="#000000",
                paper_bgcolor="#000000"
            )

            fig.update_traces(marker_line_width=0)
            
            fig.update_xaxes(
                type='category', 
                categoryorder='array', 
                categoryarray=df_chart['CHART_TIME'], 
                showticklabels=False
            )
            fig.update_yaxes(range=[0, 1.1])

            fig.add_hline(y=0.75, line_dash="dash", line_color="#FF9900")

            st.plotly_chart(fig, use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown("### EVENT_DIST::BREAKDOWN")

        if not df.empty:
            counts = df['TYPE'].value_counts().reset_index()
            counts.columns = ['TYPE', 'COUNT']

            fig2 = px.pie(
                counts,
                values='COUNT',
                names='TYPE',
                hole=0.6,
                template="plotly_dark",
                height=260
            )

            fig2.update_layout(
                showlegend=False,
                font=dict(size=10, color="#00FF41"),
                margin=dict(l=0, r=0, t=5, b=0),
                plot_bgcolor="#000000",
                paper_bgcolor="#000000"
            )

            fig2.update_traces(textposition='inside', textinfo='label+percent')
            st.plotly_chart(fig2, use_container_width=True)

# --- TABLE + ALERTS ---
col3, col4 = st.columns([7, 3])

# FIX: Added Yellow highlighting logic for the table rows
def highlight(row):
    if row['STATUS'] == 'BLOCKED':
        return ['background-color:#220000; color:#FF4444; font-weight:bold'] * len(row)
    elif row['STATUS'] == 'WARNING':
        return ['background-color:#222200; color:#FFD700; font-weight:bold'] * len(row)
    return ['color:#00FF41'] * len(row)

with col3:
    with st.container(border=True):
        st.markdown("### TXN_FEED::LIVE_BUFFER")

        if not df.empty:
            df['TIME'] = df['TIME'].dt.strftime("%H:%M:%S")
            st.dataframe(df.style.apply(highlight, axis=1),
                         use_container_width=True,
                         height=300)

with col4:
    with st.container(border=True):
        st.markdown("### ALERT_FEED::CRITICAL")

        if alerts:
            for alert in alerts[:6]:
                st.markdown(f"""
                <div style="
                    background-color:#330000;
                    color:#FF3333;
                    padding:6px;
                    border-left:4px solid #FF0000;
                    font-size:12px;
                ">
                [{alert['TIME']}] EMP::{alert['EMP']} <br>
                >> {alert['FLAGS']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(">> NO CRITICAL EVENTS")

# --- SYSTEM LOG ---
with st.container(border=True):
    st.markdown("### SYS_LOG::EVENT_STREAM")

    for row in scored_data[:10]:
        st.text(
            f"[{row['TIME']}] EVT::{row['TYPE']} | EMP::{row['EMP']} | RISK::{row['RISK']:.2f}"
        )

# --- TERMINAL FOOTER ---
st.markdown("""
<div style="color:#00FF41;">
&gt; SYSTEM ACTIVE _
</div>
""", unsafe_allow_html=True)

# --- REFRESH LOOP ---
time.sleep(2)
st.rerun()