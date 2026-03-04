import streamlit as st
import pandas as pd
from streamlit_gsheets_connection import GSheetsConnection
import george  # Ensure george.py is in your GitHub

st.set_page_config(page_title="Firm HQ: Phase 1")

# 1. Setup Connection
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏛️ Firm HQ: Phase 1 (George Only)")

# 2. George does his job
price = george.scout_live_price("bitcoin")

if price:
    st.metric("Current Bitcoin Price", f"${price:,.2f}")
    
    # 3. Record to Google Sheets
    if st.button("George: Record Price Now"):
        # Load current data
        df = conn.read(worksheet="Vault", ttl=0)
        
        # Create new row
        new_row = pd.DataFrame([{
            "Staff": "George",
            "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            "Asset": "Bitcoin",
            "Balance": price  # Recording price as balance just to test writing
        }])
        
        # Update Sheet
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Vault", data=updated_df)
        st.success("George has written to the Vault!")
else:
    st.error("George couldn't find the price. Check your internet/API.")

# 4. Show the Log
st.subheader("Vault Log")
log_df = conn.read(worksheet="Vault", ttl=0)
st.dataframe(log_df.tail(5))
