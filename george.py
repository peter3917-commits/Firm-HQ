import requests

def scout_live_price(asset="bitcoin"):
    try:
        # Fetching price from CoinGecko API
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data[asset]['usd'])
    except Exception:
        return None
