import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh # <-- The Heartbeat
import george
import arthur 
import time

st.set_page_config(page_title="Firm HQ: Auto-Sentinel", page_icon="🏛️")

# 🏛️ HQ HEADER
st.title("🏛️ Firm HQ: Auto-Sentinel")

# 🛰️ AUTO-PILOT CONTROL
st.sidebar.header("Sentinel Controls")
auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)

if auto_trade:
    # Refresh every 300,000 milliseconds (5 minutes)
    st_autorefresh(interval=300000, key="george_heartbeat")
    st.sidebar.success("George is scouting every 5 mins...")
else:
    st.sidebar.info("Manual Mode Active")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    price = george.scout_live_price("bitcoin")
    
    # 1. Pull the Vault Data
    vault_df = conn.read(worksheet="Vault", ttl=0)

    if price:
        # 2. Data Cleaning for Arthur
        if not vault_df.empty and "Balance" in vault_df.columns:
            vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
            clean_history = vault_df.dropna(subset=['Balance']).copy()
            history_for_arthur = clean_history.rename(columns={"Balance": "price_usd"})
        else:
            history_for_arthur = pd.DataFrame(columns=["price_usd"])

        # 3. Arthur's Analysis
        moving_avg, snap_pct = arthur.check_for_snap("Bitcoin", price, history_for_arthur)
        
        # 4. Market Metrics
        st.subheader("Market Intel")
        col1, col2, col3 = st.columns(3)
        col1.metric("Live BTC", f"${price:,.2f}")
        
        if moving_avg and moving_avg > 0:
            col2.metric("48h Avg", f"${moving_avg:,.2f}")
            st_color = "normal" if snap_pct > 0 else "inverse"
            col3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
        else:
            col2.info("Collecting Tape...")

        # 5. Automatic Recording Logic
        # If Auto-Scout is ON, George records the price automatically
        if auto_trade:
            # We check if the last recorded price is different or the same
            # To avoid spamming the sheet with the exact same second
            new_row = pd.DataFrame([{
                "Staff": "George (Auto)",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            updated_df = pd.concat([vault_df, new_row], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.toast("George recorded a new price entry.")

        # Manual Override Button
        elif st.button("Manual Record"):
            new_row = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            updated_df = pd.concat([vault_df, new_row], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.rerun()

    # 6. The Tape
    st.subheader("The Vault Tape")
    if not vault_df.empty:
        st.dataframe(vault_df.iloc[::-1].head(10), use_container_width=True)

except Exception as e:
    st.error(f"Sentinel Error: {e}")
