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
    Implements Fast Hook (EMA 5), 1.5% Snap, and Stage-2 Trailing Exit (WMA 5).
    """
    
    # --- INSTITUTIONAL SPREAD SIMULATION ---
    ask_price = current_price * 1.0001  # Price you pay to BUY
    bid_price = current_price * 0.9999  # Price you get when you SELL
    
    # --- CAPITAL MANAGEMENT ---
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 # Strict 10% per trade
    
    # --- STRATEGY SETTINGS ---
    TRIGGER_THRESHOLD = 1.5  # New 1.5% Gap from Magnet
    STOP_LOSS_PCT = 1.5      # New 1.5% Shield
    TARGET_OVER_MAGNET = 10.0 # 10% Moonshot Target
    
    # Default outputs
    profit = 0.0
    result = "HOLD"

    # --- SAFETY CHECK ---
    if not current_price or not average or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", WAGER_SIZE

    # --- INDICATOR PREP (EMA 5 & WMA 5) ---
    price_col = 'Balance' if 'Balance' in history_df.columns else 'price_usd'
    prices = history_df[price_col].values
    ema_5 = history_df[price_col].ewm(span=5, adjust=False).mean().iloc[-1]
    wma_5 = calculate_wma(prices, period=5)

    # --- 1. ACTIVE TRADE MONITORING (Stage-2 Trailing Exit) ---
    if os.path.exists('trades.csv'):
        df = pd.read_csv('trades.csv')
        if not df.empty:
            df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]
            mask = (df['result'] == 'OPEN') & (df['Asset'] == asset)
            
            if mask.any():
                idx = df[mask].index[-1]
                entry_price = df.at[idx, 'price']
                
                current_performance_pct = ((bid_price - entry_price) / entry_price) * 100
                hit_magnet = (bid_price >= average)
                hit_moonshot = (bid_price >= average * (1 + (TARGET_OVER_MAGNET / 100)))
                dropped_below_wma = (bid_price < wma_5)

                # EXIT LOGIC: Stage 2 Trailing
                # 1. Take the full 10% Moonshot if hit
                # 2. If above Magnet but trend breaks (Price < WMA 5), Sell.
                # 3. If still below entry, check Stop Loss.
                
                exit_triggered = False
                if hit_moonshot:
                    result = "WIN_MOONSHOT"
                    exit_triggered = True
                elif hit_magnet and dropped_below_wma:
                    result = "WIN_TRAILING"
                    exit_triggered = True
                elif current_performance_pct <= -STOP_LOSS_PCT:
                    result = "LOSS"
                    exit_triggered = True

                if exit_triggered:
                    profit = WAGER_SIZE * (current_performance_pct / 100)
                    df.at[idx, 'result'] = result
                    df.at[idx, 'profit_usd'] = profit
                    df.to_csv('trades.csv', index=False)
                    return profit, profit, result, WAGER_SIZE
                
                else:
                    floating_pl = WAGER_SIZE * (current_performance_pct / 100)
                    return 0.0, floating_pl, "OPEN", WAGER_SIZE

    # --- 2. NEW TRADE ANALYSIS (Fast Hook) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Fast Hook: Price must be above the 5-period EMA
    fast_hook = current_price > ema_5
    
    # Entry Trigger: Snap < -1.5%, RSI < 35, and Fast Hook Detected
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and fast_hook and (rsi is not None and rsi < 35)

    trade_action = "WAITING"
    if can_buy: trade_action = "BUY"

    # --- 3. EXECUTION & LOGGING ---
    if trade_action == "BUY":
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_price = ask_price
        
        new_trade = pd.DataFrame([[ts, asset, trade_action, float(execution_price), WAGER_SIZE, "OPEN", 0.0]], 
                                   columns=['timestamp','Asset','type','price','wager', 'result','profit_usd'])
        
        file_exists = os.path.exists('trades.csv')
        new_trade.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')
        return 0.0, 0.0, trade_action, WAGER_SIZE

    return 0.0, 0.0, "HOLD", WAGER_SIZE
