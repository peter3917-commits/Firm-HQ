import pandas as pd
import os
from datetime import datetime
import penny

def execute_trade(asset, current_price, average, stop_loss_pct):
    """Lawrence executes trades with specific asset logging and clean line breaks."""
    bank = penny.get_current_balance_usd()
    wager = float(bank * 0.10)

    # Validation: If price data is missing, abort trade
    if not current_price or not average or pd.isna(current_price):
        return 0.0, "SKIPPED", 0.0

    diff = ((current_price - average) / average) * 100

    # Simulation Logic
    result = "WIN" if abs(diff) > 0.5 else "LOSS"

    if result == "WIN":
        profit = float(wager * 0.02)
    else:
        profit = -float(wager * (stop_loss_pct / 100))

    # Ensure profit is not NaN
    if pd.isna(profit):
        profit = 0.0

    # Log for Sarah and the Dashboard
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ADDED: 'asset' column so Sarah knows what coin was traded
    trade_log = pd.DataFrame([[ts, asset.upper(), "SNAP", float(current_price), wager, result, profit]], 
                             columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])

    # THE FIX: lineterminator='\n' keeps the CSV rows from smashing together
    file_exists = os.path.exists('trades.csv')
    trade_log.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')

    return profit, result, wager