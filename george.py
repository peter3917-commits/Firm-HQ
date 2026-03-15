import requests

def scout_live_price(coin):
    """
    George 3.0: High-Availability Scout.
    Implements Vance Redundancy: If Primary fails, pivot to Secondary.
    """
    # 🎯 Internal Mapping
    # CoinGecko IDs (Primary)
    cg_map = {
        "Bitcoin": "bitcoin",
        "Ethereum": "ethereum",
        "Solana": "solana"
    }
    
    # Coinbase IDs (Secondary/Backup)
    cb_map = {
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD"
    }

    # --- 1. PRIMARY SCOUT: CoinGecko ---
    market_id = cg_map.get(coin)
    if market_id:
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={market_id}&vs_currencies=usd"
            # Lower timeout for faster failover
            response = requests.get(url, timeout=5) 
            
            if response.status_code == 200:
                data = response.json()
                return float(data[market_id]['usd'])
        except Exception:
            # Silent fail to trigger secondary scout
            pass

    # --- 2. SECONDARY SCOUT: Coinbase (Vance Redundancy) ---
    # If we reached here, CoinGecko failed or timed out
    backup_id = cb_map.get(coin)
    if backup_id:
        try:
            # Coinbase is excellent for high-frequency spot checks
            url = f"https://api.coinbase.com/v2/prices/{backup_id}/spot"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                price = data['data']['amount']
                return float(price)
        except Exception:
            # If both fail, return None
            return None

    return None
