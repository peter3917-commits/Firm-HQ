import pandas as pd
import os
from datetime import datetime

def get_mock_balance():
    """Temporary stand-in for Penny until she is hired."""
    return 1000.0  # Starts Lawrence with a $1,000 simulator bank

def execute_trade(asset, current_price, average, stop_loss_pct=2.0):
    """Lawrence executes trades based on the Snap logic."""
    bank = get_mock_balance()
    wager = float(bank * 0.10)

    # Validation
    if not current_price or not average or pd.isna(current_price) or average == 0:
        return 0.0, "SKIPPED", 0.0

    # Calculate Snap Difference
    diff = ((current_price - average) / average) * 100

    # Decision Logic: 
    # If Snap > 0.5% (Overextended), we 'Sell/Short'
    # If Snap < -0.5% (Undershot), we 'Buy/Long'
    if diff > 0.5:
        trade_type = "SELL"
        result = "WIN" if current_price < average else "LOSS" # Simplified for simulation
    elif diff < -0.5:
        trade_type = "BUY"
        result = "WIN" if current_price > average else "LOSS"
    else:
        return 0.0, "WAITING", 0.0

    # Calculate Profit/Loss
    if result == "WIN":
        profit = float(wager * 0.02) # 2% gain on wager
    else:
        profit = -float(wager * (stop_loss_pct / 100))

    # Log the trade
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade_log = pd.DataFrame([[ts, asset.upper(), trade_type, float(current_price), wager, result, profit]], 
                               columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])

    # Save to CSV for the Dashboard to read
    file_exists = os.path.exists('trades.csv')
    trade_log.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')

    return profit, result, wager
