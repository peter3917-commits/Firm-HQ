import streamlit as st
import pandas as pd
# IMPORTANT: The install name is st-gsheets-connection, 
# but the import name is streamlit_gsheets
from streamlit_gsheets import GSheetsConnection
import george

st.set_page_config(page_title="Firm HQ: Phase 1", page_icon="🏛️")

st.title("🏛️ Firm HQ: Phase 1")
st.write("Current focus: George scouting Bitcoin price.")

# 1. Setup the Connection to Google Sheets
try:
    # This looks for the [connections.gsheets] section in your Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Connection to Google Sheets failed. Check your Secrets setup.")
    st.stop()

# 2. Ask George for the price
# george.py must be in the same GitHub folder
price = george.scout_live_price("bitcoin")

if price:
    st.metric("Live Bitcoin Price", f"${price:,.2f}")
    
    # 3. Record the price to the 'Vault' tab
    if st.button("George: Record Price to Vault"):
        try:
            # Read existing data from the 'Vault' worksheet
            df = conn.read(worksheet="Vault", ttl=0)
            
            # Create the new entry row
            new_entry = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            
            # Combine old data with new row and send back to Google
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(worksheet="Vault", data=updated_df)
            st.success("Successfully written to the Vault!")
        except Exception as e:
            st.error(f"Failed to write to Sheet: {e}")
else:
    st.warning("George is having trouble reaching the market API. Refresh the page.")

# 4. Show the Log (last 5 entries)
st.subheader("Recent Vault Activity")
try:
    log_data = conn.read(worksheet="Vault", ttl=0)
    if not log_data.empty:
        st.dataframe(log_data.tail(5), use_container_width=True)
    else:
        st.info("The Vault is currently empty.")
except Exception:
    st.info("Waiting for data connection...")
