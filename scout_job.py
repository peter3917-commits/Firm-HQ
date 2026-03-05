import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import requests
import time

# 1. SETUP AUTH
try:
    creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    # Ensure this is your correct Sheet ID
    sheet = client.open_by_key("1rILDKQMQoLa0KDuZXFIyERBqVcKmVGUjJy4-WXhu-A4").worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

def fetch_coinbase_candles(start_time):
    """George pulls missing 5-minute candles to fill any gaps."""
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {
        'granularity': 300, # 5-minute buckets
        'start': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # Schema: [timestamp, low, high, open, close, volume]
        return pd.DataFrame(response.json(), columns=['ts', 'low', 'high', 'open', 'close', 'vol'])
    return pd.DataFrame()

# --- MAIN ENGINE ---
raw_data = sheet.get_all_records()
df = pd.DataFrame(raw_data)

if not df.empty:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=48)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()
gap_minutes = (now - last_ts).total_seconds() / 60

# Check for gaps longer than 5 minutes
if gap_minutes > 5.5:
    print(f"🕵️ George found a {int(gap_minutes)} min gap. Patching timeline...")
    history = fetch_coinbase_candles(last_ts)
    
    if not history.empty:
        # Convert Unix timestamp to readable format
        history['Timestamp'] = pd.to_datetime(history['ts'], unit='s')
        history['Balance'] = history['close']
        history['Staff'] = "George (Gap-Fill)"
        history['Asset'] = "Bitcoin"
        
        new_data = history[['Staff', 'Timestamp', 'Asset', 'Balance']]
        df = pd.concat([df, new_data], ignore_index=True)

# Always try for a current live spot price as well
try:
    live = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
    live_row = pd.DataFrame([{
        "Staff": "George (Background)",
        "Timestamp": now,
        "Asset": "Bitcoin",
        "Balance": float(live['data']['amount'])
    }])
    df = pd.concat([df, live_row], ignore_index=True)
except:
    pass

# THE SHREDDER: Keep only the most recent 48 hours
df = df.drop_duplicates(subset=['Timestamp']).sort_values('Timestamp')
cutoff = datetime.utcnow() - timedelta(hours=48)
df = df[df['Timestamp'] > cutoff]

# SYNC TO VAULT
df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
sheet.clear()
# Convert dataframe to a list of lists for gspread update
data_to_save = [df.columns.values.tolist()] + df.values.tolist()
sheet.update(data_to_save)

print(f"🏛️ Vault is now complete. Records: {len(df)}")
