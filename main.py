import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import george, arthur, lawrence, penny
from datetime import datetime, timedelta

# Institutional Wide Layout
st.set_page_config(page_title="Firm HQ: 48h Sentinel", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["Bitcoin", "Ethereum", "Solana"]

# --- 🏛️ THE FIRM HEADQUARTERS ---
# Defined at the top level to prevent NameErrors
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Firm HQ: 48h Sentinel")
    
    # Auto-Pilot Heartbeat (5 min refresh)
    auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)
    if auto_trade:
        st_autorefresh(interval=300000, key="george_heartbeat")
        st.sidebar.success("George is scouting all sectors...")

    try:
        # Establish Connection
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Pull the Vault Data
        vault_df = conn.read(worksheet="Vault", ttl=0)
        if not vault_df.empty:
            # Shield: Standardize headers
            vault_df.columns = [c.lower().strip() for c in vault_df.columns]
            
            # Type Enforcement
            bal_col = 'balance' if 'balance' in vault_df.columns else 'price_usd'
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        # 2. The Multi-Asset Sentinel Loop
        for coin in ASSETS:
            with st.container():
                price = george.scout_live_price(coin)
                
                if price:
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    
                    # Filter history for last 72h
                    asset_history = vault_df[vault_df['asset'].str.lower() == coin.lower()].copy()
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    # Market Intel Row
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.2f}")
                    
                    # Arthur's Technical Analysis
                    analysis = arthur.check_for_snap(
                        coin, price, asset_history.rename(columns={bal_col: "price_usd"})
                    )
                    
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        c2.metric("Avg Window", f"${moving_avg:,.2f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
                        # Lawrence's Execution
                        st.divider()
                        st.subheader(f"Lawrence: {coin} Execution")
                        
                        gross, net, outcome, wager = lawrence.execute_trade(
                            coin, price, moving_avg, rsi=rsi_val, history_df=asset_history
                        )
                        
                        if outcome == "OPEN":
                            st.info(f"⏳ Trade is OPEN. Floating P/L: £{net:.2f}")
                        elif "WIN" in outcome:
                            st.success(f"🎯 Outcome: {outcome} (£{net:.2f})")
                        elif outcome == "LOSS":
                            st.error(f"⚠️ Outcome: {outcome} (£{net:.2f})")
                        else:
                            st.write(f"⚖️ Lawrence is holding {coin}.")
                    else:
                        c2.info(f"📡 {coin}: Scouting...")

    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# --- 🧾 TAB 2: THE ACCOUNTING OFFICE ---
with tab2:
    st.title("💼 Firm HQ: Executive Summary")
    try:
        # 1. Gather Market Intel
        current_prices = {c: george.scout_live_price(c) for c in ASSETS}
        
        # 2. Fetch Core Ledger
        ledger = penny.get_firm_ledger(prices_dict=current_prices)
        
        if ledger and isinstance(ledger, dict):
            # 3. Calculate Live Float
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            # 4. Firm Health Metrics
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vault Cash", f"£{total_equity:,.2f}", help="Total firm value if liquidated now")
            m2.metric("Tradable Balance", f"£{ledger['tradable_balance']:,.2f}", help="Cash for new wagers")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}", delta="20% Rate", delta_color="inverse")
            m4.metric("Operational Burn", f"£{ledger.get('burn', 0):,.2f}", help="Server costs")

            st.divider()

            # 5. Institutional Table
            st.subheader("📜 Master Execution Ledger")
            desk_df = penny.format_institutional_ledger(ledger['trades_df'], current_prices)
            
            if not desk_df.empty:
                try:
                    def color_perf(val):
                        color = '#00ff00' if val > 0 else '#ff4b4b' if val < 0 else 'white'
                        return f'color: {color}'

                    st.dataframe(
                        desk_df.sort_index(ascending=False).style.applymap(
                            color_perf, subset=['Return (%)', 'P/L ($)']
                        ).format({
                            'Entry Price': '${:,.2f}',
                            'MTM Price': '${:,.2f}',
                            'Return (%)': '{:,.2f}%',
                            'P/L ($)': '£{:,.2f}'
                        }),
                        use_container_width=True, height=450
                    )
                except:
                    st.dataframe(desk_df.sort_index(ascending=False), use_container_width=True)
            else:
                st.info("No trade data detected.")
                
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
