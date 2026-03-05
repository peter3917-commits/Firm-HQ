import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import requests
import time

# 1. SETUP AUTH & CONNECTION
try:
    creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    # Using your specific Sheet ID
    sheet = client.open_by_key("1rILDKQMQoLa0KDuZXFIyERBqVcKmVGUjJy4-WXhu-A4").worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

def fetch_coinbase_candles(start_time):
    """George reaches into Coinbase to pull missing 5-minute history."""
    # Coinbase Public API for candles
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    # Granularity 300 = 5 minutes
    params = {
        'granularity': 300,
        'start': start_time.isoformat(),
        'end': datetime.now().isoformat()
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # Columns: [time, low, high, open, close, volume]
        df_hist = pd.DataFrame(response.json(), columns=['ts', 'low', 'high', 'open', 'close', 'vol'])
        return df_hist
    else:
        print(f"⚠️ Coinbase API Error: {response.status_code}")
        return pd.DataFrame()

# --- MAIN EXECUTION ---
# A. Get the current data from the Vault
raw_data = sheet.get_all_records()
df = pd.DataFrame(raw_data)

if not df.empty:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    # If sheet is empty, start from 48 hours ago
    last_ts = datetime.now() - timedelta(hours=48)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.now()
gap_seconds = (now - last_ts).total_seconds()

# B. Check for Gaps (if more than 5 minutes have passed)
if gap_seconds > 300:
    print(f"🕵️ George found a gap of {int(gap_seconds/60)} minutes. Fetching missing candles...")
    
    history = fetch_coinbase_candles(last_ts)
    
    if not history.empty:
        # Format the historical data to match our Vault
        history['Timestamp'] = pd.to_datetime(history['ts'], unit='s')
        history['Balance'] = history['close']
        history['Staff'] = "George (Gap-Fill)"
        history['Asset'] = "Bitcoin"
        
        new_entries = history[['Staff', 'Timestamp', 'Asset', 'Balance']]
        
        # Append and clean
        df = pd.concat([df, new_entries], ignore_index=True)
        print(f"✅ Recovered {len(new_entries)} missing data points.")
else:
    # No gap, just grab the current live price
    print("✨ No major gap found. Recording single live price.")
    try:
        # Falling back to a simple price check if the gap is small
        live_price_req = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot")
        price = float(live_price_req.json()['data']['amount'])
        new_row = pd.DataFrame([{
            "Staff": "George (Background)",
            "Timestamp": now,
            "Asset": "Bitcoin",
            "Balance": price
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    except:
        print("⚠️ Failed to get live price.")

# C. THE SHREDDER & REFINERY
# Remove duplicates (important when gap-filling)
df = df.drop_duplicates(subset=['Timestamp']).sort_values('Timestamp')

# Keep only the last 48 hours
cutoff = datetime.now() - timedelta(hours=48)
df = df[df['Timestamp'] > cutoff]

# D. UPDATE GOOGLE SHEETS
try:
    # Prep for upload (convert Timestamps back to strings)
    df_upload = df.copy()
    df_upload['Timestamp'] = df_upload['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    sheet.clear()
    sheet.update([df_upload.columns.values.tolist()] + df_upload.values.tolist())
    print(f"🏛️ Vault Synced: {len(df_upload)} rows now in 48h history.")
except Exception as e:
    print(f"❌ Upload Error: {e}")
