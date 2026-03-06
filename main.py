import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection  # Fixed import name
from streamlit_autorefresh import st_autorefresh
import george
import arthur
import lawrence
import penny
from datetime import datetime, timedelta

# Institutional Wide Layout
st.set_page_config(page_title="Firm HQ: 48h Sentinel", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["Bitcoin", "Ethereum", "Solana"]

# --- 🏛️ THE FIRM HEADQUARTERS ---
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

with tab1:
    st.title("🏛️ Firm HQ: 48h Sentinel")

    # 🛰️ AUTO-PILOT CONTROL
    st.sidebar.header("Sentinel Controls")
    auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)

    if auto_trade:
        st_autorefresh(interval=300000, key="george_heartbeat")
        st.sidebar.success("George is scouting all sectors...")

    try:
        # Create connection using the correct library name
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Pull the Vault Data
        try:
            vault_df = conn.read(worksheet="Vault", ttl=0)
            if not vault_df.empty:
                # Normalize column headers
                vault_df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in vault_df.columns]
                vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
                vault_df['Timestamp'] = pd.to_datetime(vault_df['Timestamp'], errors='coerce')
                vault_df = vault_df.dropna(subset=['Timestamp', 'Balance']).copy()
        except Exception:
            vault_df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

        # --- 🛰️ THE MULTI-ASSET LOOP ---
        for coin in ASSETS:
            price = george.scout_live_price(coin)
            
            if price:
                if auto_trade:
                    new_entry = pd.DataFrame([{
                        "Staff": "George (Auto)",
                        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "Asset": coin,
                        "Balance": price
                    }])
                    vault_df = pd.concat([vault_df, new_entry], ignore_index=True)

                st.divider()
                st.header(f"🛰️ Sector: {coin}")
                
                # 2. Data Filtering
                asset_history = vault_df[vault_df['Asset'] == coin].copy()
                cutoff = datetime.now() - timedelta(hours=48)
                asset_history = asset_history[asset_history['Timestamp'] > cutoff]
                history_for_arthur = asset_history.rename(columns={"Balance": "price_usd"})

                # 3. Arthur's Analysis
                moving_avg, snap_pct, rsi_val, hook_found = arthur.check_for_snap(coin, price, history_for_arthur)
                
                # 4. Market Intel Display
                st.subheader(f"Market Intel: {coin}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(f"Live {coin}", f"${price:,.2f}")
                
                if moving_avg:
                    c2.metric("48h Avg", f"${moving_avg:,.2f}")
                    st_color = "normal" if snap_pct > 0 else "inverse"
                    c3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                    c4.metric("RSI (14)", f"{rsi_val:.1f}")
                    
                    # 5. Lawrence's Execution
                    st.divider()
                    st.subheader(f"Lawrence: {coin} Execution")
                    
                    gross, net, outcome, wager = lawrence.execute_trade(
                        coin, price, moving_avg, rsi=rsi_val, prev_price=None 
                    )
                    
                    if outcome in ["BUY", "SELL"]:
                        st.warning(f"🚀 Lawrence triggered a MAJOR **{outcome}** order!")
                    elif outcome == "WIN":
                        st.success(f"🎯 Magnet Hit! (${net:.2f})")
                    elif outcome == "OPEN":
                        st.info(f"⏳ Trade is OPEN. Floating P/L: ${net:.2f}")
                    else:
                        st.write(f"⚖️ Lawrence is holding {coin}.")
                else:
                    st.info(f"Collecting 48h history for {coin}...")

        if auto_trade:
            conn.update(worksheet="Vault", data=vault_df)

    except Exception as e:
        st.error(f"System Operational Error: {e}")

# --- 🧾 TAB 2: THE ACCOUNTING OFFICE ---
with tab2:
    st.title("🧾 The Accounting Office")
    try:
        ledger = penny.get_firm_ledger()
        if ledger:
            prices_now = {
                "Bitcoin": george.scout_live_price("Bitcoin") or 70000.0,
                "Ethereum": george.scout_live_price("Ethereum") or 2500.0,
                "Solana": george.scout_live_price("Solana") or 100.0
            }
            
            unrealized_pl, open_df = penny.calculate_unrealized(ledger['trades_df'], prices_now)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Equity", f"£{total_equity:,.2f}")
            m2.metric("Vault Cash", f"£{ledger['vault_cash']:,.2f}")
            
            st.divider()
            st.subheader("📜 Master Accounting Ledger")
            # Using 'width="stretch"' as requested by the logs to replace deprecated 'use_container_width'
            st.dataframe(ledger['trades_df'], width="stretch")
    except Exception as e:
        st.error(f"Accounting Office Error: {e}")
