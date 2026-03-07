import pandas as pd
import os
from datetime import datetime
import numpy as np

def calculate_wma(prices, period=5):
    """Calculates Weighted Moving Average for the trailing exit."""
    if len(prices) < period:
        return prices[-1]
    weights = np.arange(1, period + 1)
    return (prices[-period:] * weights).sum() / weights.sum()

def execute_trade(asset, current_price, average, rsi=None, history_df=None):
    """
    Lawrence 3.0: Momentum-Reversal Execution.
    Identical logic to user version, armored for stability.
    """
    # --- INSTITUTIONAL SETTINGS ---
    ask_price = current_price * 1.0001
    bid_price = current_price * 0.9999
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 
    
    TRIGGER_THRESHOLD = 1.5  
    STOP_LOSS_PCT = 1.5      
    TARGET_OVER_MAGNET = 10.0 
    
    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", WAGER_SIZE

    # --- INDICATOR PREP ---
    price_col = 'balance' if 'balance' in [c.lower() for c in history_df.columns] else 'price_usd'
    # Find the actual case-sensitive name of the column
    actual_col = [c for c in history_df.columns if c.lower() == price_col][0]
    prices = history_df[actual_col].values
    ema_5 = history_df[actual_col].ewm(span=5, adjust=False).mean().iloc[-1]
    wma_5 = calculate_wma(prices, period=5)

    # --- 1. ACTIVE TRADE MONITORING ---
    if os.path.exists('trades.csv'):
        try:
            df = pd.read_csv('trades.csv')
            if not df.empty:
                # Force lowercase for internal logic to match Penny
                df.columns = [c.lower().strip() for c in df.columns]
                mask = (df['result'] == 'OPEN') & (df['asset'].str.lower() == asset.lower())
                
                if mask.any():
                    idx = df[mask].index[-1]
                    entry_price = df.at[idx, 'price']
                    perf = ((bid_price - entry_price) / entry_price) * 100
                    
                    # Exit Checks
                    hit_moonshot = (bid_price >= average * (1 + (TARGET_OVER_MAGNET / 100)))
                    hit_magnet_exit = (bid_price >= average and bid_price < wma_5)
                    hit_stop = (perf <= -STOP_LOSS_PCT)

                    res = "OPEN"
                    exit_now = False

                    if hit_moonshot:
                        res, exit_now = "WIN_MOONSHOT", True
                    elif hit_magnet_exit:
                        res, exit_now = "WIN_TRAILING", True
                    elif hit_stop:
                        res, exit_now = "LOSS", True

                    if exit_now:
                        pnl = WAGER_SIZE * (perf / 100)
                        df.at[idx, 'result'] = res
                        df.at[idx, 'profit_usd'] = pnl
                        df.to_csv('trades.csv', index=False)
                        return pnl, pnl, res, WAGER_SIZE
                    
                    return 0.0, WAGER_SIZE * (perf / 100), "OPEN", WAGER_SIZE
        except Exception:
            pass

    # --- 2. NEW TRADE ANALYSIS ---
    snap_pct = ((current_price - average) / average) * 100
    fast_hook = current_price > ema_5
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and fast_hook and (rsi is not None and rsi < 35)

    # --- 3. EXECUTION ---
    if can_buy:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Use lowercase columns to stay in sync with Penny
        new_row = pd.DataFrame([[ts, asset, "BUY", ask_price, WAGER_SIZE, "OPEN", 0.0]], 
                             columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])
        
        new_row.to_csv('trades.csv', mode='a', header=not os.path.exists('trades.csv'), index=False)
        return 0.0, 0.0, "BUY", WAGER_SIZE

    return 0.0, 0.0, "HOLD", WAGER_SIZE
