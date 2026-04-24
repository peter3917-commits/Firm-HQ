import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import george, arthur, lawrence, penny
from datetime import datetime, timedelta
import altair as alt

# Institutional Wide Layout
st.set_page_config(page_title="Firm HQ: 48h Sentinel", page_icon="🏛️", layout="wide")

# --- 🛰️ 2026 ASSET CONFIGURATION ---
ASSETS = {
    "Bitcoin": {"snap": 1.5, "rsi": 35},
    "Ethereum": {"snap": 2.0, "rsi": 35},
    "Solana": {"snap": 3.0, "rsi": 30}
}

# --- 🏛️ THE FIRM HEADQUARTERS ---
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Firm HQ: 48h Sentinel")
    
    # --- 🛠️ STATE MANAGEMENT & HEARTBEAT ---
    if 'scout_count' not in st.session_state:
        st.session_state.scout_count = 0

    auto_trade = st.sidebar.toggle("Activate George Auto-Scout", value=False)
    if auto_trade:
        st_autorefresh(interval=300000, key="george_heartbeat")
        st.session_state.scout_count += 1
        st.sidebar.success(f"George Heartbeat: {st.session_state.scout_count} pings")

    # --- 📊 TOP LEVEL FLEET METRICS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Scout Capacity", f"{st.session_state.scout_count} Cycles", delta="Active")
    m2.metric("Market Coverage", f"{len(ASSETS)} Sectors")
    m3.metric("Current Time", datetime.now().strftime("%H:%M:%S"))

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        ledger_data = penny.get_firm_ledger(conn)
        live_ledger_df = ledger_data['trades_df']
        tradable_cash = ledger_data.get('tradable_balance', 100.0)

        vault_df = conn.read(worksheet="Vault", ttl=0)
        if not vault_df.empty:
            vault_df.columns = [c.lower().strip() for c in vault_df.columns]
            bal_col = 'balance' if 'balance' in vault_df.columns else 'price_usd'
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce').dt.tz_localize(None)
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        for coin, targets in ASSETS.items():
            with st.container(border=True):
                price = george.scout_live_price(coin)
                if price:
                    st.header(f"🛰️ Sector: {coin}")
                    asset_history = vault_df[vault_df['asset'].str.lower() == coin.lower()].copy()
                    cutoff = datetime.now().replace(tzinfo=None) - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live Price", f"${price:,.2f}")
                    
                    analysis = arthur.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        c2.metric("Magnet (24h Avg)", f"${moving_avg:,.2f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap Deviation", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
                        # --- 📈 MAGNET VISUALIZATION ---
                        chart_cutoff = datetime.now().replace(tzinfo=None) - timedelta(hours=24)
                        chart_data = asset_history[asset_history['timestamp'] > chart_cutoff].copy()

                        if not chart_data.empty:
                            chart_df = chart_data[['timestamp', bal_col]].rename(columns={bal_col: 'Price'})
                            chart_df['Magnet'] = moving_avg 
                            
                            base = alt.Chart(chart_df).encode(x=alt.X('timestamp:T', title='Timeline (Last 24h)'))
                            
                            # Price Line
                            price_line = base.mark_line(color="#00ff00" if snap_pct > 0 else "#ff4b4b", strokeWidth=2).encode(
                                y=alt.Y('Price:Q', title='Price ($)', scale=alt.Scale(zero=False)),
                                tooltip=['timestamp', 'Price']
                            )
                            
                            # Magnet (Moving Average) Dotted Line
                            magnet_line = base.mark_line(color="white", strokeDash=[5,5], opacity=0.5).encode(y='Magnet:Q')
                            
                            st.altair_chart(price_line + magnet_line, use_container_width=True)

                        st.divider()
                        
                        gross, net, outcome, trade_data = lawrence.execute_trade(
                            coin, price, moving_avg, rsi=rsi_val, 
                            history_df=asset_history, ledger_df=live_ledger_df,
                            tradable_balance=tradable_cash
                        )
                        
                        if outcome == "BUY" and trade_data:
                            new_row = pd.DataFrame([trade_data], columns=['timestamp','asset','type','price','wager','result','profit_usd'])
                            updated_df = pd.concat([live_ledger_df, new_row], ignore_index=True)
                            conn.update(worksheet="Ledger", data=updated_df)
                            st.success(f"🚀 LAWRENCE EXECUTED: {coin}")
                            st.rerun()

                        elif outcome in ["WIN_MOONSHOT", "WIN_TRAILING", "LOSS"] and trade_data:
                            idx_to_update = trade_data['index']
                            live_ledger_df.at[idx_to_update, 'result'] = trade_data['result']
                            live_ledger_df.at[idx_to_update, 'profit_usd'] = trade_data['profit_usd']
                            conn.update(worksheet="Ledger", data=live_ledger_df)
                            st.warning(f"🎯 TRADE FINALIZED: {coin} ({outcome})")
                            st.rerun()

                        if outcome == "OPEN":
                            st.info(f"⏳ Monitoring ACTIVE trade. Floating P/L: £{net:.2f}")
                        else:
                            st.write(f"⚖️ Lawrence Status: {outcome}")

    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# --- 🧾 TAB 2: ACCOUNTING ---
with tab2:
    st.title("💼 Firm HQ: Executive Summary")
    try:
        v_df = conn.read(worksheet="Vault", ttl=0)
        current_prices = {}
        ticker_map = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL"}
        
        if not v_df.empty:
            v_df.columns = [str(c).strip().upper() for c in v_df.columns]
            for asset_name in ASSETS.keys():
                name_upper = asset_name.upper()
                asset_rows = v_df[v_df['ASSET'].str.strip().str.upper() == name_upper]
                if not asset_rows.empty:
                    raw_price = asset_rows.iloc[-1]['BALANCE']
                    try:
                        price_val = float(str(raw_price).replace(',', '').replace('$', ''))
                        current_prices[name_upper] = price_val
                        ticker = ticker_map.get(name_upper)
                        if ticker: current_prices[ticker] = price_val
                    except: continue

        ledger = penny.get_firm_ledger(conn, prices_dict=current_prices)
        if ledger and isinstance(ledger, dict):
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Equity", f"£{total_equity:,.2f}")
            m2.metric("Tradable Cash", f"£{ledger['tradable_balance']:,.2f}")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}")
            m4.metric("Burn Rate", f"£{ledger.get('burn', 0):,.2f}")
            
            st.divider()
            desk_df = penny.format_institutional_ledger(ledger['trades_df'], current_prices)
            if not desk_df.empty:
                st.dataframe(desk_df.sort_index(ascending=False), use_container_width=True, height=450)
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
