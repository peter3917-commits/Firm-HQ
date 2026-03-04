import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import george
import arthur  # <--- Arthur joins the firm

st.set_page_config(page_title="Firm HQ: Phase 2", page_icon="🏛️")
st.title("🏛️ Firm HQ: Phase 2")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. George Scouts the Price
    price = george.scout_live_price("bitcoin")
    
    # 2. Pull History for Arthur
    # We read the Vault to see what the moving average is
    try:
        vault_df = conn.read(worksheet="Vault", ttl=0)
        # We need to ensure the column is named 'price_usd' for Arthur's logic
        # Or we can temporarily rename 'Balance' to 'price_usd' for him
        history_df = vault_df.rename(columns={"Balance": "price_usd"})
    except:
        history_df = pd.DataFrame()

    if price:
        # 3. Arthur Calculates the Snap
        moving_avg, snap_pct = arthur.check_for_snap("Bitcoin", price, history_df)
        
        # Display Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Current BTC", f"${price:,.2f}")
        
        if moving_avg:
            col2.metric("48h Avg", f"${moving_avg:,.2f}")
            col3.metric("Snap %", f"{snap_pct:.2f}%", delta=f"{snap_pct:.2f}%")
        else:
            col2.info("Need more data...")
            col3.info("Awaiting tape...")

        # 4. Record Button
        if st.button("George: Record Price to Vault"):
            new_row = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            updated_df = pd.concat([vault_df, new_row], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.success("Entry added. Arthur's average will update on next refresh.")
            st.rerun()

    # Show the Log
    st.subheader("The Vault Tape")
    st.dataframe(vault_df.tail(10), use_container_width=True)

except Exception as e:
    st.error(f"Operational Error: {e}")
