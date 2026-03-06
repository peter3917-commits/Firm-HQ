import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import george
import arthur 
import lawrence 
import penny  # <--- Hiring the CFO
import os
from datetime import datetime, timedelta

# Institutional Wide Layout
st.set_page_config(page_title="Firm HQ: 48h Sentinel", page_icon="🏛️", layout="wide")

# --- 🏛️ THE FIRM HEADQUARTERS: TABBED NAVIGATION ---
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

with tab1:
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

            # 3. Arthur's Analysis (Catching 4 signals)
            moving_avg, snap_pct, rsi_val, hook_found = arthur.check_for_snap("Bitcoin", price, history_for_arthur)
            
            # 4. Market Metrics
            st.subheader("Market Intel")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Live BTC", f"${price:,.2f}")
            
            if moving_avg:
                col2.metric("48h Avg", f"${moving_avg:,.2f}")
                st_color = "normal" if snap_pct > 0 else "inverse"
                col3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                col4.metric("RSI (14)", f"{rsi_val:.1f}")
                
                # --- 🏛️ LAWRENCE'S TRADING FLOOR ---
                st.divider()
                st.subheader("Lawrence: High-Volatility Execution")
                
                if abs(snap_pct) >= 2.0:
                    status_text = "🪝 HOOK DETECTED" if hook_found else "🔪 FALLING (Wait for Hook)"
                    st.info(f"Arthur's Status: {status_text} | RSI: {rsi_val:.1f}")

                # Lawrence uses internal trades.csv
                gross, net, outcome, wager = lawrence.execute_trade(
                    "Bitcoin", price, moving_avg, rsi=rsi_val, prev_price=None 
                )
                
                if outcome in ["BUY", "SELL"]:
                    st.warning(f"🚀 Lawrence triggered a MAJOR **{outcome}** order!")
                    st.write(f"Position Size: **${wager:,.2f}** (10% of Capital)")
                elif outcome == "WIN":
                    st.success(f"🎯 Magnet Hit! Lawrence closed a WIN (${net:.2f})")
                elif outcome == "LOSS":
                    st.error(f"🛡️ Shield Active: Lawrence cut a LOSS (${net:.2f})")
                elif outcome == "OPEN":
                    st.info(f"⏳ Trade is OPEN. Lawrence is watching the Magnet. Floating P/L: ${net:.2f}")
                else:
                    st.write("⚖️ Lawrence is **holding**. (Waiting for a 2% Snap + Hook)")
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

        # 7. The Tape 
        st.subheader("📊 The Vault Tape")
        if not vault_df.empty:
            display_df = vault_df.copy()
            if pd.api.types.is_datetime64_any_dtype(display_df['Timestamp']):
                display_df['Timestamp'] = display_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(display_df.iloc[::-1].head(5), use_container_width=True)

    except Exception as e:
        st.error(f"System logic error: {e}")

# --- 🧾 TAB 2: THE ACCOUNTING OFFICE (The CFO'S Desk) ---
with tab2:
    st.title("🧾 The Accounting Office")
    ledger = penny.get_firm_ledger()
    
    if ledger:
        # Calculate live floating data using Penny's logic
        unrealized_pl, open_df = penny.calculate_unrealized(ledger['trades_df'], price)
        total_equity = ledger['vault_cash'] + unrealized_pl
        
        # --- EXECUTIVE METRICS ---
        st.subheader("Capital & Reserves")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Equity", f"£{total_equity:,.2f}", delta=f"£{unrealized_pl:,.2f} Float")
        m2.metric("Vault Cash", f"£{ledger['vault_cash']:,.2f}", help="Cash available if all trades closed now.")
        m3.metric("Tradable Balance", f"£{ledger['tradable_balance']:,.2f}", help="Vault Cash minus Tax Reserve (Money Lawrence can use)")
        m4.metric("Tax Pot", f"£{ledger['tax_pot']:,.2f}", help="20% Profit Reserve (Locked)")

        # --- OVERHEAD TRANSPARENCY ---
        with st.expander("🔍 Overhead & Friction Breakdown"):
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Fixed Burn", f"£{ledger['burn']:.2f}", help="VPS & Data Subscription costs")
            col_b.metric("Trading Friction", f"£{ledger['friction']:.2f}", help="0.15% Exchange fees + Slippage per trade")
            col_c.metric("Realized P/L", f"£{ledger['gross_realized']:,.2f}", help="Raw profit before fees and taxes")

        # --- TABLES ---
        st.divider()
        st.subheader("🔭 Live Exposure Inventory")
        if not open_df.empty:
            # We add the floating PL per position calculated by Penny
            st.dataframe(open_df.sort_index(ascending=False), use_container_width=True)
        else:
            st.info("No active exposure. All units accounted for in the Vault.")

        st.subheader("📜 Master Accounting Ledger")
        st.dataframe(ledger['trades_df'].sort_index(ascending=False), use_container_width=True)
        
        # Visual Growth (Realized)
        st.subheader("📈 Realized Performance Curve")
        chart_data = ledger['trades_df'][ledger['trades_df']['result'].isin(['WIN', 'LOSS'])].copy()
        if not chart_data.empty:
            chart_data['balance'] = 1000.00 + chart_data['profit_usd'].cumsum()
            st.line_chart(chart_data['balance'])

    else:
        st.info("Penny is awaiting data from Lawrence to begin the books.")
