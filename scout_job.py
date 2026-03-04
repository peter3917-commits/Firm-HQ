import george
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# 1. Setup Auth (Using your existing Service Account info)
# We will pull these from GitHub Secrets for security
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. Open the Vault
sheet_id = "1rILDKQMQoLa0KDuZXFIyERBqVcKmVGUjJy4-WXhu-A4"
sheet = client.open_by_key(sheet_id).worksheet("Vault")

# 3. George Scouts
price = george.scout_live_price("bitcoin")

if price:
    # 4. Pull current data for cleaning
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # 5. Add new entry
    new_entry = {
        "Staff": "George (Background)",
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Asset": "Bitcoin",
        "Balance": price
    }
    
    # 6. Shredder (Keep 48h)
    if not df.empty:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        cutoff = datetime.now() - timedelta(hours=48)
        df = df[df['Timestamp'] > cutoff]
        df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    
    # 7. Update the Vault
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"Recorded ${price} to Vault.")
