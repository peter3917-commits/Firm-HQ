import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import george

st.title("🏛️ Firm HQ: Phase 1")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    price = george.scout_live_price("bitcoin")
    
    if price:
        st.metric("Live Bitcoin Price", f"${price:,.2f}")
        
        if st.button("George: Record Price to Vault"):
            # 1. Read the sheet (or create a blank one if empty)
            try:
                df = conn.read(worksheet="Vault", ttl=0)
            except:
                df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

            # 2. Prepare the new row
            new_row = pd.DataFrame([{
                "Staff": "George",
                "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": "Bitcoin",
                "Balance": price
            }])
            
            # 3. Force the data types to match
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # 4. Write back to Google
            conn.update(worksheet="Vault", data=updated_df)
            st.success("Successfully written to the Vault!")
            st.rerun()

    # Show the Vault table
    st.subheader("Recent Vault Activity")
    log_df = conn.read(worksheet="Vault", ttl=0)
    st.dataframe(log_df, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
