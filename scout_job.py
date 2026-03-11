import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os, json, requests
import lawrence # Ensure lawrence.py is in your GitHub folder!

# 1. SETUP AUTH - SECURED FOR PUBLIC REPO
try:
    # Pulls the Service Account JSON from GitHub Secrets
    creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    
    # Pulls the Sheet ID from GitHub Secrets (prevents leaking your sheet link)
    sheet_id = os.environ.get('GSHEET_ID')
    if not sheet_id:
        raise ValueError("GSHEET_ID environment variable is missing!")
        
    sheet = client.open_by_key(sheet_id).worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

def fetch_coinbase_candles(product_id, start_time):
    url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
    params = {
        'granularity': 300,
        'start': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return pd.DataFrame(response.json(), columns=['ts', 'low', 'high', 'open', 'close', 'vol'])
    return pd.DataFrame()

# --- THE MAIN ENGINE ---

# A. GEORGE: FETCH DATA
raw_data = sheet.get_all_records()
df = pd.DataFrame(raw_data)

if not df.empty:
    # 🛡️ THE NORMALIZATION SHIELD
    df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]
    
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    # Defaulting to a 50h lookback if sheet is empty to build the initial buffer
    last_ts = datetime.utcnow() - timedelta(hours=50)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()
gap_minutes = (now - last_ts).total_seconds() / 60

# --- MULTI-ASSET GAP FILL ---
ASSETS = {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD"}

if gap_minutes > 6:
    print(f"🕵️ George found a {int(gap_minutes)} min gap. Patching sectors...")
    for asset_name, product_id in ASSETS.items():
        history = fetch_coinbase_candles(product_id, last_ts)
        if not history.empty:
            history['Timestamp'] = pd.to_datetime(history['ts'], unit='s')
            history['Balance'] = history['close']
            history['Staff'] = "George (Gap-Fill)"
            history['Asset'] = asset_name
            df = pd.concat([df, history[['Staff', 'Timestamp', 'Asset', 'Balance']]], ignore_index=True)

# Add current spot prices for all assets
for asset_name, product_id in ASSETS.items():
    try:
        live = requests.get(f"https://api.coinbase.com/v2/prices/{product_id}/spot").json()
        live_row = pd.DataFrame([{
            "Staff": "George (Background)", 
            "Timestamp": now, 
            "Asset": asset_name, 
            "Balance": float(live['data']['amount'])
        }])
        df = pd.concat([df, live_row], ignore_index=True)
    except:
        pass

# Ensure we keep multi-asset records and remove exact duplicates
df = df.drop_duplicates(subset=['Timestamp', 'Asset']).sort_values('Timestamp')

# B. ARTHUR & LAWRENCE: SECTOR ANALYSIS
for asset_name in ASSETS.keys():
    asset_df = df[df['Asset'] == asset_name].copy()
    if not asset_df.empty:
        asset_df['Balance'] = pd.to_numeric(asset_df['Balance'])
        
        # Arthur calculates the "Magnet" using the last 576 points (exactly 48 hours)
        magnet = asset_df['Balance'].tail(576).mean()
        current_price = float(asset_df['Balance'].iloc[-1])
        
        # C. LAWRENCE: EXECUTE
        gross, net, result, wager = lawrence.execute_trade(asset_name, current_price, magnet)
        
        print(f"Sect: {asset_name} | Price: ${current_price:,.2f} | Magnet: ${magnet:,.2f} | Law: {result}")

# D. SHRED & HIGH-SPEED SYNC
cutoff = datetime.utcnow() - timedelta(hours=50)
df = df[df['Timestamp'] > cutoff]

if not df.empty:
    df_sync = df[['Staff', 'Timestamp', 'Asset', 'Balance']].copy()
    df_sync['Timestamp'] = df_sync['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    data_to_save = [df_sync.columns.values.tolist()] + df_sync.values.tolist()
    try:
        sheet.clear()
        sheet.update(range_name='A1', values=data_to_save)
        print(f"✅ Vault synchronized. Current Depth: {len(df_sync)} rows across 3 sectors.")
    except Exception as e:
        print(f"⚠️ Vault sync delay: {e}")
