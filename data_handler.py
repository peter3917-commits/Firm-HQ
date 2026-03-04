import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def get_vault_connection():
    """Establishes connection to the Google Sheet defined in Streamlit Secrets."""
    return st.connection("gsheets", type=GSheetsConnection)

def load_vault():
    """Reads the current status of the firm from Google Sheets."""
    try:
        conn = get_vault_connection()
        # It looks for a sheet named 'Vault'
        data = conn.read(worksheet="Vault", ttl="0") 
        return data
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        # Returns an empty dataframe with your specific columns as a fallback
        return pd.DataFrame(columns=['Staff', 'Balance', 'Last_Trade', 'Status'])

def update_vault(df):
    """Overwrites the Google Sheet with the new updated DataFrame."""
    try:
        conn = get_vault_connection()
        conn.update(worksheet="Vault", data=df)
        return True
    except Exception as e:
        st.error(f"Failed to save data to Google Sheets: {e}")
        return False