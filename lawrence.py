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
    Standardized to match Penny's lowercase ledger format.
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
    cols_lower = [c.lower() for c in history_df.columns]
    if 'balance' in cols_lower:
        price_col = history_df.columns[cols_lower.index('balance')]
    elif 'price_usd' in cols_lower:
        price_col = history_df.columns[cols_lower.index('price_usd')]
    else:
        return 0.0, 0.0, "DATA_ERROR", WAGER_SIZE

    prices_arr = history_df[price_col].values
    ema_5 = history_df[price_col].ewm(span=5, adjust=False).mean().iloc[-1]
    wma_5 = calculate_wma(prices_arr, period=5)

    # --- 1. ACTIVE TRADE MONITORING ---
    if os.path.exists('trades.csv'):
        try:
            # Read and keep original headers for writing back accurately
            df = pd.read_csv('trades.csv')
            if not df.empty:
                # Use a temp list for case-insensitive matching
                cols_check = [c.lower().strip() for c in df.columns]
                
                # Identify column indices
                res_idx = cols_check.index('result')
                ast_idx = cols_check.index('asset')
                prc_idx = cols_check.index('price')
                pnl_idx = cols_check.index('profit_usd')

                # Filter for OPEN trades for this specific asset
                # Use .iloc to ensure we are modifying the original dataframe structure
                for i in range(len(df)):
                    if str(df.iloc[i, res_idx]).upper() == 'OPEN' and str(df.iloc[i, ast_idx]).lower() == asset.lower():
                        entry_price = float(df.iloc[i, prc_idx])
                        perf = ((bid_price - entry_price) / entry_price) * 100
                        
                        # Exit Condition Logic
                        hit_moonshot = (bid_price >= average * (1 + (TARGET_OVER_MAGNET / 100)))
                        hit_magnet_trend_break = (bid_price >= average and bid_price < wma_5)
                        hit_stop = (perf <= -STOP_LOSS_PCT)

                        outcome = "OPEN"
                        exit_triggered = False

                        if hit_moonshot:
                            outcome, exit_triggered = "WIN_MOONSHOT", True
                        elif hit_magnet_trend_break:
                            outcome, exit_triggered = "WIN_TRAILING", True
                        elif hit_stop:
                            outcome, exit_triggered = "LOSS", True

                        if exit_triggered:
                            pnl_val = WAGER_SIZE * (perf / 100)
                            df.iloc[i, res_idx] = outcome
                            df.iloc[i, pnl_idx] = pnl_val
                            df.to_csv('trades.csv', index=False)
                            return pnl_val, pnl_val, outcome, WAGER_SIZE
                        
                        # If still open, return current floating P/L
                        return 0.0, WAGER_SIZE * (perf / 100), "OPEN", WAGER_SIZE
        except Exception as e:
            print(f"Lawrence Error: {e}")
            pass

    # --- 2. NEW TRADE ANALYSIS ---
    snap_pct = ((current_price - average) / average) * 100
    fast_hook = current_price > ema_5
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and fast_hook and (rsi is not None and rsi < 35)

    # --- 3. EXECUTION ---
    if can_buy:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.DataFrame([[ts, asset, "BUY", ask_price, WAGER_SIZE, "OPEN", 0.0]], 
                             columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])
        
        new_row.to_csv('trades.csv', mode='a', header=not os.path.exists('trades.csv'), index=False)
        return 0.0, 0.0, "BUY", WAGER_SIZE

    return 0.0, 0.0, "HOLD", WAGER_SIZE
