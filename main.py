import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import george
import arthur 
import lawrence 
import time
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Firm HQ: 48h Sentinel", page_icon="🏛️")
st.title("🏛️ Firm HQ: 48h Sentinel")

# 🛰️ AUTO-PILOT CONTROL
st.sidebar.header("Sentinel Controls")
auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)

if auto_trade:
    st_autorefresh(interval=300000, key="george_heartbeat")
    st.sidebar.success("George is scouting...")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    price = george.scout_live_price("bitcoin")
    
    # 1. Pull the Vault Data
    try:
        vault_df = conn.read(worksheet="Vault", ttl=0)
    except Exception:
        vault_df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

    if price:
        # 2. DATA CLEANING & 48H SHREDDER
        if not vault_df.empty and "Timestamp" in vault_df.columns:
            vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
            vault_df['Timestamp'] = pd.to_datetime(vault_df['Timestamp'], errors='coerce')
            vault_df = vault_df.dropna(subset=['Timestamp', 'Balance']).copy()
            
            cutoff = datetime.now() - timedelta(hours=48)
            vault_df = vault_df[vault_df['Timestamp'] > cutoff].copy()
            history_for_arthur = vault_df.rename(columns={"Balance": "price_usd"})
        else:
            history_for_arthur = pd.DataFrame(columns=["price_usd"])

        # 3. Arthur's Analysis
        moving_avg, snap_pct = arthur.check_for_snap("Bitcoin", price, history_for_arthur)
        
        # 4. Market Metrics
        st.subheader("Market Intel")
        col1, col2, col3 = st.columns(3)
        col1.metric("Live BTC", f"${price:,.2f}")
        
        if moving_avg:
            col2.metric("48h Avg", f"${moving_avg:,.2f}")
            st_color = "normal" if snap_pct > 0 else "inverse"
            col3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
            
            # --- 🏛️ LAWRENCE'S TRADING FLOOR ---
            st.divider()
            st.subheader("Lawrence: High-Volatility Execution")
            st.caption("Strategy: 2.0% Snap Trigger | 0.5% Stop-Loss")
            
            # UPDATED: Catching 4 values: gross, net, outcome, wager
            gross, net, outcome, wager = lawrence.execute_trade("Bitcoin", price, moving_avg)
            
            if outcome in ["BUY", "SELL"]:
                st.warning(f"🚀 Lawrence triggered a MAJOR **{outcome}** order!")
                st.write(f"Position Size: **${wager:,.2f}**")
            elif outcome == "WIN":
                st.success(f"🎯 Magnet Hit! Lawrence closed a WIN (${net:.2f})")
            elif outcome == "LOSS":
                st.error(f"🛡️ Shield Active: Lawrence cut a LOSS (${net:.2f})")
            elif outcome == "OPEN":
                st.info(f"⏳ Trade is OPEN. Lawrence is watching the Magnet. Current P/L: ${net:.2f}")
            else:
                st.write("⚖️ Lawrence is **holding**. (Waiting for a 2% Snap)")
        else:
            st.info("Collecting data for Arthur...")

        # 5. Recording Logic
        st.divider()
        if auto_trade or st.button("Manual Record"):
            new_entry = pd.DataFrame([{
                "Staff": "George (Auto)" if auto_trade else "George",
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            updated_df = pd.concat([vault_df, new_entry], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            if not auto_trade: st.rerun()

    # 6. Trade Ledger
    if os.path.exists('trades.csv'):
        st.subheader("📜 Lawrence's Trade Ledger")
        trades_df = pd.read_csv('trades.csv')
        st.dataframe(trades_df.iloc[::-1].head(10), use_container_width=True)

    # 7. The Tape
    st.subheader("📊 The Vault Tape")
    if not vault_df.empty:
        display_df = vault_df.copy()
        if pd.api.types.is_datetime64_any_dtype(display_df['Timestamp']):
            display_df['Timestamp'] = display_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(display_df.iloc[::-1].head(10), use_container_width=True)

except Exception as e:
    st.error(f"System logic error: {e}")
