import streamlit as st
import pandas as pd
from streamlit_gsheets_connection import GSheetsConnection
import george

st.set_page_config(page_title="Firm HQ: Phase 1", page_icon="🏛️")

st.title("🏛️ Firm HQ: Phase 1")
st.write("Current focus: George scouting Bitcoin price.")

# 1. Setup the Connection to Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Connection to Google Sheets failed. Check your Secrets.")
    st.stop()

# 2. Ask George for the price
price = george.scout_live_price("bitcoin")

if price:
    st.metric("Live Bitcoin Price", f"${price:,.2f}")
    
    # 3. Record the price to the 'Vault' tab
    if st.button("George: Record Price to Vault"):
        try:
            # Read existing data
            df = conn.read(worksheet="Vault", ttl=0)
            
            # Create the new entry
            new_entry = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            
            # Combine and Update
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.success("Successfully written to the Vault!")
        except Exception as e:
            st.error(f"Failed to write to Sheet: {e}")
else:
    st.warning("George is having trouble reaching the market. Refresh the page.")

# 4. Show the Log
st.subheader("Recent Vault Activity")
try:
    log_data = conn.read(worksheet="Vault", ttl=0)
    st.dataframe(log_data.tail(5), use_container_width=True)
except:
    st.info("The Vault is currently empty.")
