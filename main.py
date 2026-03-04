import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets_connection import GSheetsConnection

# --- 1. CLOUD UI CONFIG ---
st.set_page_config(page_title="Firm-HQ Cloud", layout="wide", page_icon="🏛️")
st_autorefresh(interval=30000, key="hq_refresh")

# --- 2. DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_vault_cloud():
    # ttl=0 ensures we get live data from the sheet every time
    return conn.read(ttl=0) 

# --- 3. THE ENGINE TICK ---
def run_firm_tick():
    try:
        import george, arthur, lawrence, penny, sarah
        # Background tasks
        penny.take_taxes_and_overheads()
        
        for asset_name in ["bitcoin", "ethereum"]:
            price = george.scout_live_price(asset_name)
            history = george.get_recent_history(asset_name)
            if price is not None and not history.empty:
                avg, diff = arthur.check_for_snap(asset_name, price, history)
                if abs(diff) >= 0.4:
                    p_l, res, wager = lawrence.execute_trade(asset_name, price, avg, 0.5)
                    if res != "SKIPPED":
                        sarah.report_trade(asset_name, res, avg, price, 0, p_l, 0)
    except Exception as e:
        # We show engine errors in the sidebar so the main UI stays clean
        st.sidebar.error(f"Staff Error: {e}")

# --- 4. DASHBOARD UI ---
LONDON_TZ = pytz.timezone('Europe/London')
now = datetime.now(LONDON_TZ)

st.title("🏛️ Firm HQ: Cloud Monitor")

# Load the data
df = load_vault_cloud()

if not df.empty:
    # Helper to find columns regardless of hidden spaces or small typos
    def find_col(name, dataframe):
        for c in dataframe.columns:
            if name.lower() in c.lower():
                return c
        return None

    bal_col = find_col('Balance', df)
    staff_col = find_col('Staff', df)
    
    if bal_col:
        current_bal = df[bal_col].iloc[-1]
        last_staff = df[staff_col].iloc[-1] if staff_col else "Unknown"
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Vault Balance", f"${float(current_bal):,.2f}")
        c2.metric("Last Action By", last_staff)
        c3.metric("London Time", now.strftime('%H:%M:%S'))
        
        st.subheader("📝 Recent Ledger Entries")
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.error(f"Could not find 'Balance' column. Headers detected: {list(df.columns)}")
else:
    st.warning("GSheet is connected but appears to be empty.")

# Run the background logic
run_firm_tick()

# Run one "Tick" of the engine on every refresh
run_firm_tick()
