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
                # 🛡️ NORMALIZATION SHIELD (Force standard lowercase for logic processing)
                vault_df.columns = [c.lower().strip() for c in vault_df.columns]
                
                # --- 🕵️ X-RAY DEBUGGER ---
                st.sidebar.divider()
                st.sidebar.caption("🛰️ Sentinel X-Ray")
                st.sidebar.write("Columns:", list(vault_df.columns))
                
                # Handle potential casing variations from Sheets
                bal_col = 'balance' if 'balance' in vault_df.columns else 'Balance'
                ts_col = 'timestamp' if 'timestamp' in vault_df.columns else 'Timestamp'
                ast_col = 'asset' if 'asset' in vault_df.columns else 'Asset'

                vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
                vault_df[ts_col] = pd.to_datetime(vault_df[ts_col], errors='coerce')
                
                raw_rows = len(vault_df)
                vault_df = vault_df.dropna(subset=[ts_col, bal_col]).copy()
                valid_rows = len(vault_df)
                
                if valid_rows > 0:
                    st.sidebar.info(f"📁 Vault: {valid_rows} active records.")
                else:
                    st.warning(f"⚠️ Found {raw_rows} rows in Sheets, but the data format is invalid.")
        except Exception as e:
            st.error(f"Vault Read Error: {e}")
            vault_df = pd.DataFrame(columns=["staff", "timestamp", "asset", "balance"])

        # --- 🛰️ THE MULTI-ASSET LOOP ---
        for coin in ASSETS:
            with st.container():
                price = george.scout_live_price(coin)
                
                if price:
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    
                    # 2. Data Shredding (Using the Normalized Lowercase Columns)
                    asset_history = vault_df[vault_df['asset'].str.lower() == coin.lower()].copy()
                    
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    # 3. Market Intel Columns
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.2f}")
                    
                    # 4. Arthur's Analysis (Renaming for Arthur's logic)
                    analysis = arthur.check_for_snap(
                        coin, price, asset_history.rename(columns={"balance": "price_usd"})
                    )
                    
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        
                        c2.metric("Avg Window", f"${moving_avg:,.2f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
                        # 5. Lawrence's Execution
                        st.divider()
                        st.subheader(f"Lawrence: {coin} Execution")
                        
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
            # Ensure trades_df exists and has the expected columns before displaying
            if not ledger['trades_df'].empty:
                st.dataframe(ledger['trades_df'].sort_index(ascending=False), width="stretch")
                
                if 'result' in ledger['trades_df'].columns and 'LEGACY_CLEANUP' in ledger['trades_df']['result'].values:
                    st.toast("🧹 Penny just cleaned up legacy ghost trades.", icon="🧹")
            else:
                st.info("No trades recorded in the ledger yet.")
                
    except Exception as e:
        st.error(f"Accounting Office Error: {e}")
