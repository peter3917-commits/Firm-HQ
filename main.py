import streamlit as st
import pandas as pd
from streamlit_gsheets_connection import GSheetsConnection
import george

st.set_page_config(page_title="Firm HQ: Phase 1", layout="centered")

st.title("🏛️ Firm HQ: Phase 1")

# 1. Establish Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Connection Setup Failed: {e}")
    st.stop()

# 2. Get Data from George
try:
    price = george.scout_live_price("bitcoin")
    if price:
        st.metric("Current Bitcoin Price", f"${price:,.2f}")
    else:
        st.warning("George is waiting for market data...")
except Exception as e:
    st.error(f"George Error: {e}")

# 3. Reading and Writing Logic
if st.button("Record to Google Sheets"):
    try:
        # worksheet="Vault" matches your tab name
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
    except Exception as e:
        st.error(f"Writing Failed: {e}")

# 4. Show current Vault contents
st.subheader("Current Vault Records")
try:
    log_df = conn.read(worksheet="Vault", ttl=0)
    st.dataframe(log_df, use_container_width=True)
except:
    st.info("Vault is currently empty or connecting...")
