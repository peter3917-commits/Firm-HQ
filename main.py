import streamlit as st
import pandas as pd
import pytz
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets_connection import GSheetsConnection

# --- 1. CLOUD UI CONFIG ---
st.set_page_config(page_title="Firm-HQ Cloud", layout="wide", page_icon="🏛️")

# Refresh the dashboard every 30 seconds
st_autorefresh(interval=30000, key="hq_refresh")

# --- 2. THE DATA CONNECTION ---
# This replaces the old data_handler logic with the official cloud version
conn = st.connection("gsheets", type=GSheetsConnection)

def load_vault_cloud():
    # Ensure the name "Sheet1" matches your actual Tab name in Google Sheets
    return conn.read(ttl="0") 

# --- 3. THE ENGINE (MODERNIZED) ---
# Instead of a complex thread, we run a "Check" every time the page refreshes
def run_firm_tick():
    import george, arthur, lawrence, penny, sarah
    
    # 1. Penny handles overheads
    penny.take_taxes_and_overheads()
    
    # 2. George & Arthur scout
    for asset in ["bitcoin", "ethereum"]:
        price = george.scout_live_price(asset)
        history = george.get_recent_history(asset)

        if price is not None and not history.empty:
            avg, diff = arthur.check_for_snap(asset, price, history)

            # 3. Lawrence Trades
            if abs(diff) >= 0.4:
                p_l, res, wager = lawrence.execute_trade(asset, price, avg, 0.5)
                
                if res != "SKIPPED":
                    # Sarah reports it (This updates your GSheet via your existing sarah.py logic)
                    sarah.report_trade(asset, res, avg, price, 0, p_l, 0) 

# --- 4. DASHBOARD UI ---
LONDON_TZ = pytz.timezone('Europe/London')
now = datetime.now(LONDON_TZ)

st.title("🏛️ Firm HQ: Cloud Monitor")
st.write(f"**System Status:** Operational | **London Time:** {now.strftime('%H:%M:%S')}")

# Load Data
vault_df = load_vault_cloud()

if not vault_df.empty:
    # Use the column name exactly as it appears in your Google Sheet (Case Sensitive!)
    current_bal = vault_df['Balance'].iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Vault Balance", f"${current_bal:,.2f}")
    col2.metric("Staff Status", "Active")
    col3.metric("Cloud Connection", "Stable")

    st.subheader("📝 Recent Ledger Entries")
    st.dataframe(vault_df.tail(10), use_container_width=True)
else:
    st.warning("Connected to GSheets, but no data found. Check your Column names!")

# Run one "Tick" of the engine on every refresh
run_firm_tick()
