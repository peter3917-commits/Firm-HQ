import pandas as pd
import os
from datetime import datetime

def execute_trade(asset, current_price, average, rsi=None, prev_price=None):
    """
    Lawrence 2.0: Now with Capital Management and Active Trade detection.
    Aiming for 50% Win Rate with 4:1 Reward-to-Risk.
    """
    
    # --- CAPITAL MANAGEMENT ---
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 # Strict £100 per trade
    
    # --- STRATEGY SETTINGS ---
    TRIGGER_THRESHOLD = 2.0  # 2% Gap
    STOP_LOSS_PCT = 0.5      # 0.5% Shield
    
    # Initial status
    trade_type = "WAITING"
    profit = 0.0
    result = "HOLD"

    # --- SAFETY CHECK ---
    if not current_price or not average or average == 0:
        return 0.0, 0.0, "WAITING", WAGER_SIZE

    # --- ACTIVE TRADE CHECK (The 'One-at-a-time' Rule) ---
    if os.path.exists('trades.csv'):
        existing_trades = pd.read_csv('trades.csv')
        # Check if there are any rows where 'result' is still 'OPEN'
        if not existing_trades.empty and (existing_trades['result'] == 'OPEN').any():
            # If a trade is open, Lawrence's only job is to see if it's time to CLOSE it
            active_trade = existing_trades[existing_trades['result'] == 'OPEN'].iloc[-1]
            entry_price = active_trade['price']
            
            # Calculate distance from entry for the Shield or the Magnet
            # (Simplifying: we check if price moved back to average or hit SL)
            current_move = ((current_price - entry_price) / entry_price) * 100
            
            # Logic to close a BUY trade
            if active_trade['type'] == "BUY":
                if current_price >= average: # Target Hit
                    return float(WAGER_SIZE * 0.02), float(WAGER_SIZE * 0.02), "WIN", WAGER_SIZE
                elif current_move <= -STOP_LOSS_PCT: # Shield Broken
                    return -float(WAGER_SIZE * 0.005), -float(WAGER_SIZE * 0.005), "LOSS", WAGER_SIZE
                else:
                    return 0.0, 0.0, "OPEN", WAGER_SIZE

    # --- ARTHUR'S PATIENCE FILTERS (The Jury) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # 1. THE STRIKE (Only if no trade is open)
    # We add a small 'Hook' check: only buy if price is slightly higher than prev_price
    is_hooked = True
    if prev_price and current_price < prev_price:
        is_hooked = False # Still falling, wait for the hook!

    if snap_pct <= -TRIGGER_THRESHOLD and is_hooked:
        trade_type = "BUY"
    elif snap_pct >= TRIGGER_THRESHOLD and is_hooked:
        trade_type = "SELL"

    # 2. LOGGING NEW TRADES
    if trade_type != "WAITING":
        result = "OPEN"
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade_log = pd.DataFrame([[ts, asset.upper(), trade_type, float(current_price), WAGER_SIZE, result, 0.0]], 
                                   columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])
        
        file_exists = os.path.exists('trades.csv')
        trade_log.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')

    # Return the 4 values required by the Scout engine
    return profit, profit, result, WAGER_SIZE
