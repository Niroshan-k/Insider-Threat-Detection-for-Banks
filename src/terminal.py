import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timezone, timedelta
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
st.set_page_config(page_title="Terminal", layout="wide")

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
        font-family: 'JetBrains Mono', monospace !important;
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
    
    /* --- FIX: BROKEN ICONS & OVERLAP --- */
    /* 1. Restore the icon font so it draws an arrow instead of spelling "_arrow_down" */
    .stIcon, span[class*="material-symbols"], [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary svg {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        letter-spacing: normal !important;
        color: #00FF41 !important; /* Hacker green arrow */
    }

    /* 2. Force a flexbox layout to push the arrow to the far right */
    [data-testid="stExpander"] summary {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding-right: 10px !important;
    }

    [data-testid="stExpander"] summary p {
        flex-grow: 1 !important; /* Makes the text take up the left space */
        font-weight: bold !important;
        color: #FF9900 !important; /* Terminal orange text */
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://localhost:27017/")["ndb_insider_threat"]

db = init_connection()

# --- HEADER ---
st.markdown("## SOC TERMINAL")
now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"SYSTEM TIME::{now_utc} UTC // STATUS::ACTIVE")

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
            "TIME_OBJ": action.get("timestamp"), # <--- THIS IS THE MISSING KEY
            "EMP": row["EMP"],
            "FLAGS": ", ".join(score["anomalyFlags"])
        })

df = pd.DataFrame(scored_data)

# --- CALCULATE CBSL DEADLINE (MOVED DOWN HERE) ---
cbsl_deadline = "N/A"
deadline_status = "STANDBY"

if alerts:
    # Get the raw time of the most recent alert
    first_alert_time = alerts[0]['TIME_OBJ']  
    
    # Ensure timezone awareness for the math
    if first_alert_time.tzinfo is None:
        first_alert_time = first_alert_time.replace(tzinfo=timezone.utc)

    # CBSL Mandate: 2 Hours to report
    deadline = first_alert_time + timedelta(hours=2)
    cbsl_deadline = deadline.strftime("%H:%M:%S")
    
    # Calculate time remaining in minutes
    time_remaining = (deadline - datetime.now(timezone.utc)).total_seconds() / 60
    if time_remaining < 0:
        deadline_status = f"⚠️ OVERDUE by {abs(int(time_remaining))}m"
    else:
        deadline_status = f"⏱️ {int(time_remaining)}m remaining"
        
# --- METRICS ---
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("DB LATENCY", "1.1ms")
    m2.metric("STREAM STATUS", "ACTIVE")
    m3.metric("EVENT BUFFER", str(len(df)))
    m4.metric("ALERT COUNT", str(len(alerts)))

# --- CHARTS ---
col1, col2 = st.columns([7, 3])

with col1:
    with st.container(border=True):
        st.markdown("### VOLATILITY INDEX")

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
                showticklabels=True,  # Show every 10th label
                tickangle=45,
                tickmode='linear',
                tick0=0,
                dtick=10
            )
            fig.update_yaxes(range=[0, 1.1])

            fig.add_hline(y=0.75, line_dash="dash", line_color="#FF9900")

            st.plotly_chart(fig, use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown("### EVENT DISTRIBUTION")

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
                showlegend=True, # FIX 1: Turn the legend ON
                legend=dict(
                    title=None,  # Hides the redundant 'TYPE' title above the color boxes
                    orientation="v", # Vertical list
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.0, # Pushes it neatly to the right of the donut
                    font=dict(size=10, color="#FFFFFF") # Keeps it terminal green
                ),
                font=dict(size=10, color="#00FF41"),
                margin=dict(l=0, r=0, t=5, b=0),
                plot_bgcolor="#000000",
                paper_bgcolor="#000000"
            )

            # FIX 2: Stop forcing the labels inside the chart, just show the math
            fig2.update_traces(textposition='inside', textinfo='percent')
            
            st.plotly_chart(fig2, use_container_width=True)

# --- TABLE + ALERTS ---
col3, col4 = st.columns([7, 3])

def highlight(row):
    # 1. BLOCKED (Red Row)
    if row['STATUS'] == 'BLOCKED':
        return ['background-color:#220000; color:#FF4444; font-weight:bold'] * len(row)
        
    # 2. WARNING (Yellow Row)
    elif row['STATUS'] == 'WARNING':
        return ['background-color:#222200; color:#FFD700; font-weight:bold'] * len(row)
        
    # 3. NORMAL (White Data, Green Status)
    else:
        styles = []
        for col in row.index:
            if col in ['TIME', 'EMP', 'TYPE', 'IP']:
                styles.append('color:#FFFFFF') # Standard terminal white for raw data
            else:
                styles.append('color:#00FF41') # Hacker green for RISK and STATUS
        return styles

with col3:
    with st.container(border=True):
        
        # --- 1. DETERMINE FEED STATUS ---
        is_live = False
        if not df.empty:
            # Grab the absolute newest transaction time (Row 0)
            # We force it to UTC just in case, to make the math perfectly safe
            latest_time = pd.to_datetime(df['TIME'].iloc[0], utc=True)
            now_time = pd.Timestamp.now(tz='UTC')
            
            # How many seconds ago was the last database insert?
            seconds_since_last_txn = (now_time - latest_time).total_seconds()
            
            # If a transaction arrived in the last 10 seconds, the pumper is running
            if seconds_since_last_txn < 5:
                is_live = True

        # --- 2. BUILD THE DYNAMIC HEADER ---
        if is_live:
            # Bright Hacker Green box with black text
            badge = '<span style="background-color:#00FF41; color:#000000; padding:2px 8px; font-size:20px;">LIVE</span>'
        else:
            # Dim Gray/Red box for offline mode
            badge = '<span style="background-color:#F8423B; color:#000000; padding:2px 8px; font-size:20px;">STANDBY</span>'

        st.markdown(f"### TRANSACTION FEED BUFFER {badge}", unsafe_allow_html=True)

        # --- 3. RENDER THE TABLE ---
        if not df.empty:
            # We use a copy here so we don't break any charts relying on the original df
            df_display = df.copy()
            df_display['TIME'] = df_display['TIME'].dt.strftime("%H:%M:%S")
            
            st.dataframe(df_display.style.apply(highlight, axis=1),
                         use_container_width=True,
                         height=300)

with col4:
    with st.container(border=True):
        st.markdown("### ALERT")
        
        # Show CBSL countdown at top
        st.markdown(f"""
        <div style="
            background-color:#440000;
            color:#FF9900;
            padding:8px;
            border:2px solid #FF0000;
            margin-bottom:10px;
            font-size:14px;
            font-weight:bold;
        ">
        CBSL REPORTING DEADLINE: {cbsl_deadline} ({deadline_status})
        </div>
        """, unsafe_allow_html=True)

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

# --- EMPLOYEE DRILL-DOWN ---
with st.expander("🔍 EMPLOYEE_PROFILE::FORENSIC_VIEW", expanded=False):
    with st.container(border=True):
        emp_filter = st.selectbox("SELECT_TARGET_ID:", ["ALL"] + sorted(df['EMP'].unique().tolist()))
        
        if emp_filter != "ALL":
            # Use .copy() to prevent Pandas warnings when modifying the time format
            emp_actions = df[df['EMP'] == emp_filter].copy()
            
            st.markdown(f"### FORENSIC TARGET::{emp_filter}")
            
            # Spread metrics across 4 columns for a sleeker dashboard look
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("TOTAL ACTIONS", len(emp_actions))
            c2.metric("AVG RISK SCORE", f"{emp_actions['RISK'].mean():.2f}")
            c3.metric("WARNINGS ISSUED", len(emp_actions[emp_actions['STATUS'] == 'WARNING']))
            c4.metric("CRITICAL BLOCKS", len(emp_actions[emp_actions['STATUS'] == 'BLOCKED']))
            
            st.markdown("---")
            st.markdown("### TARGET EVENT LOG")
            
            # Reformat time and apply the exact same CSS highlighting as the main table!
            emp_actions['TIME'] = pd.to_datetime(emp_actions['TIME']).dt.strftime("%H:%M:%S")
            st.dataframe(
                emp_actions.style.apply(highlight, axis=1), 
                use_container_width=True, 
                height=250
            )
        else:
            st.markdown(">> AWAITING_TARGET_SELECTION...")

# --- SYSTEM LOG ---
with st.container(border=True):
    st.markdown("### SYS_LOG::EVENT_STREAM")

    for row in scored_data[:10]:
        st.text(
            f"[{row['TIME']}] EVT::{row['TYPE']} | EMP::{row['EMP']} | RISK::{row['RISK']:.2f}"
        )

# --- REFRESH LOOP ---
time.sleep(2)
st.rerun()