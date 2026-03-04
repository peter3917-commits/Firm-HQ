import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import george
import arthur 

st.set_page_config(page_title="Firm HQ: Phase 2", page_icon="🏛️")
st.title("🏛️ Firm HQ: Phase 2")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. George Scouts the Price
    price = george.scout_live_price("bitcoin")
    
    # 2. Pull the Vault Data
    try:
        vault_df = conn.read(worksheet="Vault", ttl=0)
    except:
        vault_df = pd.DataFrame()

    # 3. The HQ Control Room
    if price:
        # --- DATA CLEANER ---
        if not vault_df.empty and "Balance" in vault_df.columns:
            # Force 'Balance' to be a number, turning errors into 'NaN'
            vault_df['Balance'] = pd.to_numeric(vault_df['Balance'], errors='coerce')
            # Drop any rows where the balance didn't convert correctly
            clean_history = vault_df.dropna(subset=['Balance']).copy()
            # Arthur needs the column named 'price_usd'
            history_for_arthur = clean_history.rename(columns={"Balance": "price_usd"})
        else:
            history_for_arthur = pd.DataFrame(columns=["price_usd"])

        # --- ARTHUR'S LOGIC ---
        moving_avg, snap_pct = arthur.check_for_snap("Bitcoin", price, history_for_arthur)
        
        # --- DISPLAY ---
        st.subheader("Market Intel")
        col1, col2, col3 = st.columns(3)
        col1.metric("Live BTC", f"${price:,.2f}")
        
        if moving_avg and moving_avg > 0:
            col2.metric("48h Avg", f"${moving_avg:,.2f}")
            col3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%")
        else:
            col2.info("Awaiting Tape...")
            col3.info("Awaiting Tape...")

        # 4. Record Button
        st.divider()
        if st.button("George: Record Current Price"):
            new_row = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            updated_df = pd.concat([vault_df, new_row], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.success("Entry added. Refreshing...")
            st.rerun()

    # 5. The Log (Always Visible)
    st.subheader("The Vault Tape")
    if not vault_df.empty:
        st.dataframe(vault_df.tail(10), use_container_width=True)
    else:
        st.info("The Vault is currently empty.")

except Exception as e:
    st.error(f"System logic error: {e}")
