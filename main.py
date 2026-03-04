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
            # Force numeric and datetime types
            vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
            vault_df['Timestamp'] = pd.to_datetime(vault_df['Timestamp'], errors='coerce')
            
            # DROP garbage rows to prevent .dt accessor errors
            vault_df = vault_df.dropna(subset=['Timestamp', 'Balance']).copy()
            
            # SHREDDER: Keep only the last 48 hours
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
            col
