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
        # 1. VAULT-FIRST DATA RETRIEVAL (The "George-is-Writing" Fix)
        # We look at the actual Vault sheet first because George is updating it every 5 mins.
        v_df = conn.read(worksheet="Vault", ttl=0)
        current_prices = {}
        ticker_map = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL"}
        
        if not v_df.empty:
            # Shield: Standardize Vault column names
            v_df.columns = [str(c).strip().upper() for c in v_df.columns]
            
            for asset_name in ASSETS:
                name_upper = asset_name.upper()
                # Find the LATEST entry for this asset
                asset_rows = v_df[v_df['ASSET'].str.strip().str.upper() == name_upper]
                
                if not asset_rows.empty:
                    # Get price from 'BALANCE' column (as per your vault structure)
                    raw_price = asset_rows.iloc[-1]['BALANCE']
                    try:
                        price_val = float(raw_price)
                        current_prices[name_upper] = price_val
                        ticker = ticker_map.get(name_upper)
                        if ticker:
                            current_prices[ticker] = price_val
                    except:
                        continue

        # 2. API FALLBACK: If Vault sync failed for any reason, try George's Scout
        for asset_name in ASSETS:
            name_up = asset_name.upper()
            if name_up not in current_prices:
                p = george.scout_live_price(asset_name)
                if p:
                    current_prices[name_up] = p
                    t = ticker_map.get(name_up)
                    if t: current_prices[t] = p
        
        # UI FEEDBACK
        if "BTC" in current_prices:
            st.success(f"📟 Vault & Market Sync Active: BTC @ ${current_prices['BTC']:,.2f}")
        else:
            st.warning("⚠️ Market Data Sync Issues: Using ledger defaults.")

        # 3. FETCH CORE LEDGER
        ledger = penny.get_firm_ledger(prices_dict=current_prices)
        
        if ledger and isinstance(ledger, dict):
            # 4. CALCULATE LIVE FLOAT
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            # 5. FIRM HEALTH METRICS
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vault Value", f"£{total_equity:,.2f}", help="Live Valuation")
            m2.metric("Tradable", f"£{ledger['tradable_balance']:,.2f}")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}")
            m4.metric("Burn", f"£{ledger.get('burn', 0):,.2f}")

            st.divider()

            # 6. MASTER EXECUTION LEDGER (With Force-Update Safeties)
            st.subheader("📜 Master Execution Ledger")
            desk_df = penny.format_institutional_ledger(ledger['trades_df'], current_prices)
            
            if not desk_df.empty:
                # TYPE SAFETY: Ensure MTM and Return are handled even if the word 'BTC' is lowercase in CSV
                for idx, row in desk_df.iterrows():
                    ticker_in_row = str(row['Ticker']).strip().upper()
                    if row['Status'] == "🟢 ACTIVE" and ticker_in_row in current_prices:
                        live_val = current_prices[ticker_in_row]
                        entry_val = row['Entry Price']
                        
                        # Apply live data injection
                        desk_df.at[idx, 'MTM Price'] = live_val
                        new_ret = ((live_val - entry_val) / entry_val) * 100
                        desk_df.at[idx, 'Return (%)'] = new_ret
                        
                        # P/L logic: wager * return
                        wager_orig = ledger['trades_df'].iloc[idx]['wager']
                        desk_df.at[idx, 'P/L ($)'] = wager_orig * (new_ret / 100)

                # 7. DISPLAY (Fixed Streamlit Syntax)
                st.dataframe(
                    desk_df.sort_index(ascending=False).style.map(
                        lambda x: f'color: {"#00ff00" if x > 0 else "#ff4b4b" if x < 0 else "white"}', 
                        subset=['Return (%)', 'P/L ($)']
                    ).format({
                        'Entry Price': '${:,.2f}', 'MTM Price': '${:,.2f}',
                        'Return (%)': '{:,.2f}%', 'P/L ($)': '£{:,.2f}'
                    }),
                    width=None, # Replaces use_container_width to avoid log warnings
                    height=450
                )
            else:
                st.info("No trade data detected.")
                
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
