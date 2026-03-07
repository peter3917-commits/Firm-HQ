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

with tab1:
    st.title("🏛️ Firm HQ: 48h Sentinel")
    
    # 🛰️ AUTO-PILOT CONTROL
    auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)
    if auto_trade:
        st_autorefresh(interval=300000, key="george_heartbeat")
        st.sidebar.success("George is scouting all sectors...")

    try:
        # Establish Connection
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Pull the Vault Data
        try:
            vault_df = conn.read(worksheet="Vault", ttl=0)
            if not vault_df.empty:
                # 🛡️ NORMALIZATION SHIELD
                vault_df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in vault_df.columns]
                
                vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
                vault_df['Timestamp'] = pd.to_datetime(vault_df['Timestamp'], errors='coerce')
                
                # --- 🕵️ DEBUG CHECK ---
                raw_rows = len(vault_df)
                vault_df = vault_df.dropna(subset=['Timestamp', 'Balance']).copy()
                valid_rows = len(vault_df)
                
                if valid_rows > 0:
                    st.sidebar.info(f"📁 Vault: {valid_rows} active records.")
                else:
                    st.warning(f"⚠️ Found {raw_rows} rows in Sheets, but the data format is invalid.")
        except Exception as e:
            st.error(f"Vault Read Error: {e}")
            vault_df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

        # --- 🛰️ THE MULTI-ASSET LOOP ---
        for coin in ASSETS:
            # Containerizing the coin ensures one doesn't block the other
            with st.container():
                price = george.scout_live_price(coin)
                
                if price:
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    
                    # 2. Data Shredding
                    # Use case-insensitive matching for "bitcoin" vs "Bitcoin"
                    asset_history = vault_df[vault_df['Asset'].str.lower() == coin.lower()].copy()
                    
                    # Widened window for early-stage collection (19h data is fine here)
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['Timestamp'] > cutoff]
                    
                    # 3. Market Intel Columns
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.2f}")
                    
                    # 4. Arthur's Analysis (Safe Check)
                    # We pass the history even if small so Arthur can attempt WMA/EMA
                    analysis = arthur.check_for_snap(
                        coin, price, asset_history.rename(columns={"Balance": "price_usd"})
                    )
                    
                    # Check if Arthur returned a valid tuple
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        
                        c2.metric("Avg Window", f"${moving_avg:,.2f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
                        # 5. Lawrence's Execution
                        st.divider()
                        st.subheader(f"Lawrence: {coin} Execution")
                        
                        # Note: We pass history_df=asset_history as required by your new Lawrence code
                        gross, net, outcome, wager = lawrence.execute_trade(
                            coin, price, moving_avg, rsi=rsi_val, history_df=asset_history
                        )
                        
                        if outcome in ["BUY", "SELL"]:
                            st.warning(f"🚀 Lawrence triggered a MAJOR **{outcome}** order on {coin}!")
                        elif outcome == "WIN":
                            st.success(f"🎯 Magnet Hit! Lawrence closed a WIN (£{net:.2f})")
                        elif outcome == "WIN_MOONSHOT":
                            st.success(f"🚀 MOONSHOT! Lawrence exited with maximum profit (£{net:.2f})")
                        elif outcome == "WIN_TRAILING":
                            st.success(f"📈 Trailing Exit! Lawrence exited on WMA 5 break (£{net:.2f})")
                        elif outcome == "OPEN":
                            st.info(f"⏳ Trade is OPEN. Floating P/L: £{net:.2f}")
                        else:
                            st.write(f"⚖️ Lawrence is holding {coin}.")
                    else:
                        # This keeps ETH/SOL on the screen even if they have low history
                        c2.info(f"📡 {coin}: Scouting...")
                        c3.write(f"Vault Data: {len(asset_history)} points")
                        c4.caption("Need 14+ points for RSI")

    except Exception as e:
        st.error(f"System Operational Error: {e}")

# --- 🧾 TAB 2: THE ACCOUNTING OFFICE ---
with tab2:
    st.title("🧾 The Accounting Office")
    try:
        current_prices = {c: george.scout_live_price(c) for c in ASSETS}
        ledger = penny.get_firm_ledger(prices_dict=current_prices)
        
        if ledger:
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Equity", f"£{total_equity:,.2f}", delta=f"£{unrealized_pl:,.2f} Float")
            m2.metric("Vault Cash", f"£{ledger['vault_cash']:,.2f}")
            m3.metric("Tradable Balance", f"£{ledger['tradable_balance']:,.2f}")
            m4.metric("Tax Pot", f"£{ledger['tax_pot']:,.2f}")

            st.divider()
            st.subheader("📜 Master Accounting Ledger")
            st.dataframe(ledger['trades_df'].sort_index(ascending=False), width="stretch")
            
            if 'LEGACY_CLEANUP' in ledger['trades_df']['result'].values:
                st.toast("🧹 Penny just cleaned up legacy ghost trades.", icon="🧹")
                
    except Exception as e:
        st.error(f"Accounting Office Error: {e}")
