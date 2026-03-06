import requests

def scout_live_price(coin):
    """
    George's improved scouting logic. 
    Connects to the market to fetch real-time USD prices.
    """
    # 🎯 Internal Mapping: Link your names to the market IDs
    coin_map = {
        "Bitcoin": "bitcoin",
        "Ethereum": "ethereum",
        "Solana": "solana"
    }
    
    # Get the correct ID for the API
    market_id = coin_map.get(coin)
    
    if not market_id:
        return None

    try:
        # George calls the simple price endpoint
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={market_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Extract the price from the nested JSON
            price = data[market_id]['usd']
            return float(price)
        else:
            return None
            
    except Exception as e:
        # If the scout hits a wall, return None so the Sentinel can skip safely
        return None
