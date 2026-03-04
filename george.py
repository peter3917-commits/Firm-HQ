import requests

def scout_live_price(asset="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset}&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return float(data[asset]['usd'])
    except Exception as e:
        return None
