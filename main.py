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
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Firm HQ: 48h Sentinel")
    
    auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)
    if auto_trade:
        st_autorefresh(interval=300000, key="george_heartbeat")
        st.sidebar.success("George is scouting all sectors...")

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        vault_df = conn.read(worksheet="Vault", ttl=0)
        if not vault_df.empty:
            vault_df.columns = [c.lower().strip() for c in vault_df.columns]
            bal_col = 'balance' if 'balance' in vault_df.columns else 'price_usd'
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        for coin in ASSETS:
            with st.container():
                price = george.scout_live_price(coin)
                if price:
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    asset_history = vault_df[vault_df['asset'].str.lower() == coin.lower()].copy()
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.2f}")
                    
                    analysis = arthur.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        c2.metric("Avg Window", f"${moving_avg:,.2f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
                        st.divider()
                        st.subheader(f"Lawrence: {coin} Execution")
                        gross, net, outcome, wager = lawrence.execute_trade(coin, price, moving_avg, rsi=rsi_val, history_df=asset_history)
                        
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
        # 1. LIVE DATA INJECTION
        # We manually fetch prices here to bridge George's names to Penny's tickers
        btc_p = george.scout_live_price("Bitcoin")
        eth_p = george.scout_live_price("Ethereum")
        sol_p = george.scout_live_price("Solana")
        
        current_prices = {
            "BITCOIN": btc_p, "BTC": btc_p,
            "ETHEREUM": eth_p, "ETH": eth_p,
            "SOLANA": sol_p, "SOL": sol_p
        }
        
        # UI FEEDBACK: Verify the data is actually arriving in main.py
        if btc_p:
            st.success(f"📟 Live Market Feed: BTC @ ${btc_p:,.2f}")
        else:
            st.warning("⚠️ Market Feed Offline: George could not fetch Bitcoin price.")

        # 2. FETCH CORE LEDGER
        ledger = penny.get_firm_ledger(prices_dict=current_prices)
        
        if ledger and isinstance(ledger, dict):
            # 3. CALCULATE LIVE FLOAT
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            # 4. FIRM HEALTH METRICS
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vault Value", f"£{total_equity:,.2f}", help="Live Valuation")
            m2.metric("Tradable", f"£{ledger['tradable_balance']:,.2f}")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}")
            m4.metric("Burn", f"£{ledger.get('burn', 0):,.2f}")

            st.divider()

            # 5. MASTER EXECUTION LEDGER (With Direct Price Enforcement)
            st.subheader("📜 Master Execution Ledger")
            desk_df = penny.format_institutional_ledger(ledger['trades_df'], current_prices)
            
            if not desk_df.empty:
                # FORCE UPDATE: Ensure the table shows the live price we just fetched
                for idx, row in desk_df.iterrows():
                    ticker = str(row['Ticker']).upper().strip()
                    if row['Status'] == "🟢 ACTIVE" and ticker in current_prices:
                        live_val = current_prices[ticker]
                        if live_val:
                            entry_val = row['Entry Price']
                            # Recalculate metrics in the UI layer
                            desk_df.at[idx, 'MTM Price'] = live_val
                            new_ret = ((live_val - entry_val) / entry_val) * 100
                            desk_df.at[idx, 'Return (%)'] = new_ret
                            
                            # Update P/L based on the wager from the original trades file
                            wager_val = ledger['trades_df'].iloc[idx]['wager']
                            desk_df.at[idx, 'P/L ($)'] = wager_val * (new_ret / 100)

                # 6. DISPLAY WITH UPDATED STREAMLIT SYNTAX
                st.dataframe(
                    desk_df.sort_index(ascending=False).style.map(
                        lambda x: f'color: {"#00ff00" if x > 0 else "#ff4b4b" if x < 0 else "white"}', 
                        subset=['Return (%)', 'P/L ($)']
                    ).format({
                        'Entry Price': '${:,.2f}', 'MTM Price': '${:,.2f}',
                        'Return (%)': '{:,.2f}%', 'P/L ($)': '£{:,.2f}'
                    }),
                    width=None, # Replaces use_container_width
                    height=450
                )
            else:
                st.info("No trade data detected.")
                
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
