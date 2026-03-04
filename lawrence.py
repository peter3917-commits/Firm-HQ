import pandas as pd
import os
from datetime import datetime

def execute_trade(asset, current_price, average):
    """Lawrence: High-Volatility Reversion Specialist."""
    bank = 1000.0  
    wager = float(bank * 0.10) # $100 wagers
    
    if not current_price or not average or average == 0:
        return 0.0, "WAITING", 0.0

    snap_pct = ((current_price - average) / average) * 100
    
    # --- STRATEGY SETTINGS ---
    TRIGGER_THRESHOLD = 2.0  # Only strike at 2% gap
    STOP_LOSS_PCT = 0.5      # Cut losses at 0.5%
    
    trade_type = "WAITING"
    profit = 0.0
    result = "HOLD"

    # 1. THE STRIKE
    if snap_pct <= -TRIGGER_THRESHOLD:
        trade_type = "BUY" # Buying the dip
    elif snap_pct >= TRIGGER_THRESHOLD:
        trade_type = "SELL" # Fading the pump

    # 2. THE OUTCOME (Simulation Logic)
    if trade_type != "WAITING":
        # If the gap is closing, Lawrence wins big
        if abs(snap_pct) < 0.1: # Price hit the average
            result = "WIN"
            profit = float(wager * (TRIGGER_THRESHOLD / 100)) # 2% profit
        # If it goes 0.5% further against us, hit the shield
        elif abs(snap_pct) > (TRIGGER_THRESHOLD + STOP_LOSS_PCT):
            result = "LOSS"
            profit = -float(wager * (STOP_LOSS_PCT / 100)) # 0.5% loss
        else:
            result = "OPEN"
            profit = 0.0

    # 3. LOGGING
    if trade_type != "WAITING":
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade_log = pd.DataFrame([[ts, asset.upper(), trade_type, float(current_price), wager, result, profit]], 
                                   columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])
        file_exists = os.path.exists('trades.csv')
        trade_log.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')

    return profit, result, wager
