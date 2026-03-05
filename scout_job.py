import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os, json, requests
import lawrence # Ensure lawrence.py is in your GitHub folder!

# 1. SETUP AUTH
try:
    creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1rILDKQMQoLa0KDuZXFIyERBqVcKmVGUjJy4-WXhu-A4").worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

def fetch_coinbase_candles(start_time):
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
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
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=48)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()
gap_minutes = (now - last_ts).total_seconds() / 60

# We check for gaps over 6 minutes to avoid unnecessary calls during normal heartbeats
if gap_minutes > 6:
    print(f"🕵️ George found a {int(gap_minutes)} min gap. Patching...")
    history = fetch_coinbase_candles(last_ts)
    if not history.empty:
        history['Timestamp'] = pd.to_datetime(history['ts'], unit='s')
        history['Balance'] = history['close']
        history['Staff'] = "George (Gap-Fill)"
        history['Asset'] = "Bitcoin"
        df = pd.concat([df, history[['Staff', 'Timestamp', 'Asset', 'Balance']]], ignore_index=True)

# Add current spot price
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

df = df.drop_duplicates(subset=['Timestamp']).sort_values('Timestamp')

# B. ARTHUR: ANALYZE
df['Balance'] = pd.to_numeric(df['Balance'])
magnet = df['Balance'].tail(576).mean()
current_price = float(df['Balance'].iloc[-1])
snap_pct = ((current_price - magnet) / magnet) * 100

# C. LAWRENCE: EXECUTE
gross, net, result, wager = lawrence.execute_trade("BTC", current_price, magnet)

# D. SHRED & HIGH-SPEED SYNC
cutoff = datetime.utcnow() - timedelta(hours=48)
df = df[df['Timestamp'] > cutoff]

if not df.empty:
    df_sync = df[['Staff', 'Timestamp', 'Asset', 'Balance']].copy()
    df_sync['Timestamp'] = df_sync['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # NEW: The "Traffic-Jam" Fix. We overwrite starting at A1 in one single batch.
    data_to_save = [df_sync.columns.values.tolist()] + df_sync.values.tolist()
    try:
        # sheet.clear() is removed to save time/API calls
        sheet.update(range_name='A1', values=data_to_save)
        print("✅ Vault synchronized successfully.")
    except Exception as e:
        print(f"⚠️ Vault sync delay: {e}")

# --- THE FIRM'S LOG ---
print("-" * 30)
print(f"🏛️ Firm Heartbeat | {datetime.now().strftime('%H:%M:%S')}")
print(f"📈 Price: ${current_price:,.2f} | Magnet: ${magnet:,.2f}")
print(f"⚡ Snap: {snap_pct:.2f}%")
print(f"📢 Lawrence says: {result} | Wager: ${wager:.2f}")
print(f"💰 Net Profit: ${net:.2f}")
print("-" * 30)
