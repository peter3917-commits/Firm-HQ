import george
import arthur
import lawrence
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# 1. Setup Auth
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. Open the Vault
sheet_id = "1rILDKQMQoLa0KDuZXFIyERBqVcKmVGUjJy4-WXhu-A4"
sheet = client.open_by_key(sheet_id).worksheet("Vault")

# 3. George Scouts the Live Price
price = george.scout_live_price("bitcoin")

if price:
    # 4. Pull current data for cleaning and analysis
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # 5. Data Cleaning (Ensure numeric for Arthur)
    if not df.empty:
        df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce')
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df = df.dropna(subset=['Timestamp', 'Balance'])

    # 6. Arthur & Lawrence: The Strategy Floor
    # Create the history format Arthur expects
    history_for_arthur = df.rename(columns={"Balance": "price_usd"})
    
    # Arthur calculates the 48h Average
    moving_avg, snap_pct = arthur.check_for_snap("Bitcoin", price, history_for_arthur)
    
    # Lawrence evaluates the 2% Snap
    if moving_avg:
        lawrence.execute_trade("Bitcoin", price, moving_avg)

    # 7. Add George's New Entry to the Tape
    new_entry = {
        "Staff": "George (Background)",
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Asset": "Bitcoin",
        "Balance": price
    }
    
    # 8. Shredder (Keep only last 48h in the Google Sheet)
    cutoff = datetime.now() - timedelta(hours=48)
    df = df[df['Timestamp'] > cutoff].copy()
    
    # Convert back to string format for Google Sheets update
    df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Combine with new entry
    final_df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    
    # 9. Secure the Vault
    sheet.clear()
    sheet.update([final_df.columns.values.tolist()] + final_df.values.tolist())
    
    print(f"Recorded ${price} to Vault. Snap was {snap_pct:.2f}%. Lawrence evaluated.")
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"Recorded ${price} to Vault.")
