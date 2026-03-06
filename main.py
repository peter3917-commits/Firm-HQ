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

# --- 🧾 TAB 2: ACCOUNTING OFFICE (CFO UPGRADE) ---
with tab2:
    st.title("🧾 The Accounting Office")
    
    if os.path.exists('trades.csv'):
        trades_df = pd.read_csv('trades.csv')
        
        # --- institutional Accounting ---
        INITIAL_CAPITAL = 1000.00
        
        # 1. Realized Accounting (The Cash in the Vault)
        closed_trades = trades_df[trades_df['result'].isin(['WIN', 'LOSS'])]
        realized_profit = closed_trades['profit_usd'].sum()
        vault_balance = INITIAL_CAPITAL + realized_profit
        
        # 2. Unrealized Accounting (The Trades in the Field)
        open_trades = trades_df[trades_df['result'] == 'OPEN']
        exposure_at_risk = open_trades['wager'].sum()
        
        unrealized_pl = 0.0
        if not open_trades.empty and 'price' in locals():
            for _, row in open_trades.iterrows():
                entry_p = row['price']
                wager_v = row['wager']
                if row['type'] == "BUY":
                    unrealized_pl += wager_v * ((price - entry_p) / entry_p)
                else:
                    unrealized_pl += wager_v * ((entry_p - price) / entry_p)
        
        total_equity = vault_balance + unrealized_pl
        
        # --- FINANCIAL METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Equity", f"£{total_equity:,.2f}", delta=f"£{unrealized_pl:,.2f} Floating")
        m2.metric("Vault Balance", f"£{vault_balance:,.2f}", help="Cash available if all trades closed now.")
        m3.metric("Exposure at Risk", f"£{exposure_at_risk:,.2f}", help="Total capital currently in active trades.")
        m4.metric("Realized P/L", f"£{realized_profit:,.2f}")

        # --- 🔭 OPEN INVENTORY ---
        st.divider()
        st.subheader("🔭 Open Positions Inventory")
        if not open_trades.empty:
            st.dataframe(open_trades.sort_index(ascending=False), use_container_width=True)
        else:
            st.info("No active exposure. All capital is safe.")

        # --- 📜 MASTER LEDGER ---
        st.subheader("📜 Historical Ledger")
        ledger_display = trades_df.sort_index(ascending=False)
        st.dataframe(ledger_display, use_container_width=True)
        
        # Performance Curve
        if not closed_trades.empty:
            st.subheader("📈 Performance Curve (Realized)")
            closed_trades = closed_trades.copy()
            closed_trades['cum_profit'] = INITIAL_CAPITAL + closed_trades['profit_usd'].cumsum()
            st.line_chart(closed_trades['cum_profit'])
    else:
        st.info("The Ledger is currently empty.")
