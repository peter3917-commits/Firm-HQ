import requests

def scout_live_price(asset_name="Bitcoin"):
    """
    George 2.0: Multi-Asset Scout.
    Mapping display names to CoinGecko IDs to ensure the Vault remains clean.
    """
    # Map your Vault names to the API's required IDs
    ticker_map = {
        "Bitcoin": "bitcoin",
        "Ethereum": "ethereum",
        "Solana": "solana"
    }
    
    # Default to bitcoin if the name isn't in our map
    api_id = ticker_map.get(asset_name, "bitcoin")

    try:
        # Fetching price from CoinGecko API
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={api_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Extract price using the API ID
        return float(data[api_id]['usd'])
    except Exception:
        return None
