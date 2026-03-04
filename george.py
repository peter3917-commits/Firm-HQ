import requests

def scout_live_price(asset="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        return float(response.json()[asset]['usd'])
    except:
        return None
