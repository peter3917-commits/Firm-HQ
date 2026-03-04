import pandas as pd
import requests
from data_handler import load_vault

def scout_live_price(asset):
    """Fetches the live price from CoinGecko API."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset}&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return data[asset]['usd']
    except Exception as e:
        print(f"📡 George Price Error ({asset}): {e}")
        return None

def get_recent_history(asset):
    """Fetches trade history from Google Sheets."""
    try:
        df = load_vault()
        if df.empty or 'Asset' not in df.columns:
            return pd.DataFrame()

        # Filter for the specific asset (e.g., 'bitcoin')
        asset_history = df[df['Asset'] == asset]
        return asset_history
    except Exception as e:
        print(f"📡 George History Error: {e}")
        return pd.DataFrame()