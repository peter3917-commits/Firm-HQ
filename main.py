import streamlit as st

# --- ERROR CATCHER ---
# This must be the very first thing to ensure the app doesn't crash silently
try:
    import pandas as pd
    from streamlit_gsheets_connection import GSheetsConnection
    import george
    
    st.set_page_config(page_title="Firm HQ: Phase 1", layout="centered")
    st.title("🏛️ Firm HQ: Phase 1")

    # 1. Establish Connection
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 2. Get Data from George
    price = george.scout_live_price("bitcoin")
    if price:
        st.metric("Current Bitcoin Price", f"${price:,.2f}")
    else:
        st.warning("George is waiting for market data...")

    # 3. Reading and Writing Logic
    if st.button("Record to Google Sheets"):
        df = conn.read(worksheet="Vault", ttl=0)
        
        new_row = pd.DataFrame([{
            "Staff": "George",
            "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            "Asset": "Bitcoin",
            "Balance": price
        }])
        
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Vault", data=updated_df)
        st.success("Data written to Google Sheets!")

    # 4. Show current Vault contents
    st.subheader("Current Vault Records")
    log_df = conn.read(worksheet="Vault", ttl=0)
    st.dataframe(log_df, use_container_width=True)

except Exception as e:
    st.error("🚨 APP CRASHED DURING STARTUP")
    st.exception(e)
