import streamlit as st
from streamlit_gsheets_connection import GSheetsConnection
import pandas as pd

def get_vault_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def load_vault():
    try:
        conn = get_vault_connection()
        # worksheet="Vault" matches your tab name exactly (Capital V)
        data = conn.read(worksheet="Vault", ttl="0") 
        return data
    except Exception as e:
        st.error(f"Error reading sheet 'Vault': {e}")
        # Fallback columns in case the sheet is totally blank
        return pd.DataFrame(columns=['Staff', 'Timestamp', 'Asset', 'Type', 'Entry', 'Exit', 'P_L', 'Balance'])

def update_vault(df):
    try:
        conn = get_vault_connection()
        # Updates the specific 'Vault' tab
        conn.update(worksheet="Vault", data=df)
        return True
    except Exception as e:
        st.error(f"Failed to save to 'Vault': {e}")
        return False
