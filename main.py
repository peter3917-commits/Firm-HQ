import streamlit as st
import pandas as pd
import pytz
import threading
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from data_handler import load_vault, update_vault

# --- 1. CLOUD UI CONFIG ---
st.set_page_config(page_title="Firm HQ", layout="wide")
st_autorefresh(interval=10000, key="hq_refresh")

# --- 2. THE BACKGROUND ENGINE ---
@st.cache_resource
def start_firm_engine():
    def heartbeat_loop():
        # Delayed imports to keep startup fast
        import george, arthur, lawrence, penny, sarah
        time.sleep(5) 

        while True:
            try:
                # The Staff does their rounds
                penny.take_taxes_and_overheads()
                for asset in ["bitcoin", "ethereum"]:
                    price = george.scout_live_price(asset)
                    history = george.get_recent_history(asset)

                    if price and not history.empty:
                        avg, diff = arthur.check_for_snap(asset, price, history)

                        if abs(diff) >= 0.4:
                            p_l, res, wager = lawrence.execute_trade(asset, price, avg, 0.5)

                            if res != "SKIPPED":
                                # UPDATED: Using Cloud Data Handler
                                vault_df = load_vault()
                                current_bal = vault_df['Balance'].iloc[-1]

                                # Create new row for the cloud update
                                new_bal = current_bal + p_l
                                # (Note: You may need to adjust columns to match your Sheet exactly)
                                update_vault(vault_df) # Logic for adding row would go here

                                sarah.report_trade(asset, res, avg, price, 0, p_l, new_bal)
            except Exception as e:
                print(f"Engine Error: {e}")
            time.sleep(300)

    thread = threading.Thread(target=heartbeat_loop, daemon=True)
    thread.start()
    return True

# Trigger the engine
engine_active = start_firm_engine()

# --- 3. THE DASHBOARD ---
LONDON_TZ = pytz.timezone('Europe/London')
now = datetime.now(LONDON_TZ)

st.title("🏛️ Firm HQ: Live Monitor")
st.sidebar.success("Cloud Engine Active")
st.write(f"**London Time:** {now.strftime('%H:%M:%S')}")

# --- 4. DATA LOADING FROM GOOGLE SHEETS ---
vault_df = load_vault()

# Fallback if sheet is empty
if not vault_df.empty:
    vault_bal = vault_df['Balance'].iloc[-1]
else:
    vault_bal = 1000.00

# UI Metrics
c1, c2 = st.columns(2)
c1.metric("Vault Balance (Live GSheets)", f"${vault_bal:,.2f}")
c2.metric("Status", "Operational")

# Tabs
t1, t2 = st.tabs(["📡 George", "📝 Sarah"])
with t1:
    st.write("George is scouting market data...")
    # Your live chart logic goes here

with t2:
    st.subheader("Cloud Trade Ledger")
    # For now, displaying the vault history from the sheet
    st.dataframe(vault_df.tail(10), use_container_width=True)