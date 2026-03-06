import pandas as pd
import os
from datetime import datetime

def execute_trade(asset, current_price, average, rsi=None, prev_price=None):
    """
    Lawrence 2.0: High-Volatility Execution Specialist.
    FIXED: Argument names matched to main.py to prevent 'unexpected keyword' errors.
    """
    
    # --- CAPITAL MANAGEMENT ---
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 # Strict £100 per trade
    
    # --- STRATEGY SETTINGS ---
    TRIGGER_THRESHOLD = 2.0  # 2% Gap from Magnet
    STOP_LOSS_PCT = 0.5      # 0.5% Shield
    
    # Default outputs
    profit = 0.0
    result = "HOLD"

    # --- SAFETY CHECK ---
    if not current_price or not average or average == 0:
        return 0.0, 0.0, "WAITING", WAGER_SIZE

    # --- 1. ACTIVE TRADE MONITORING ---
    if os.path.exists('trades.csv'):
        df = pd.read_csv('trades.csv')
        if not df.empty and (df['result'] == 'OPEN').any():
            # Get the details of the current open trade
            idx = df[df['result'] == 'OPEN'].index[-1]
            entry_price = df.at[idx, 'price']
            trade_type = df.at[idx, 'type']
            
            # Calculate current performance
            diff_pct = ((current_price - entry_price) / entry_price) * 100
            if trade_type == "SELL": diff_pct = -diff_pct
            
            # EXIT LOGIC: Target (Magnet) or Shield (Stop Loss)
            hit_magnet = (trade_type == "BUY" and current_price >= average) or \
                         (trade_type == "SELL" and current_price <= average)

            if hit_magnet:
                result = "WIN"
                profit = WAGER_SIZE * (abs(current_price - entry_price) / entry_price)
                df.at[idx, 'result'] = "WIN"
                df.at[idx, 'profit_usd'] = profit
                df.to_csv('trades.csv', index=False)
                return profit, profit, "WIN", WAGER_SIZE

            elif diff_pct <= -STOP_LOSS_PCT:
                result = "LOSS"
                profit = -(WAGER_SIZE * (STOP_LOSS_PCT / 100))
                df.at[idx, 'result'] = "LOSS"
                df.at[idx, 'profit_usd'] = profit
                df.to_csv('trades.csv', index=False)
                return profit, profit, "LOSS", WAGER_SIZE
            
            else:
                floating_pl = WAGER_SIZE * (diff_pct / 100)
                return 0.0, floating_pl, "OPEN", WAGER_SIZE

    # --- 2. NEW TRADE ANALYSIS (THE JURY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Calculate 'The Hook' from the prev_price provided by main.py
    hook_detected = False
    if prev_price is not None and current_price > prev_price:
        hook_detected = True
    
    # Criteria for a BUY: 2% Snap + Hook Detected + RSI Oversold (<35)
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and hook_detected and (rsi is not None and rsi < 35)
    
    # Criteria for a SELL: 2% Snap + Price not hooking + RSI Overbought (>65)
    can_sell = (snap_pct >= TRIGGER_THRESHOLD) and (not hook_detected) and (rsi is not None and rsi > 65)

    trade_action = "WAITING"
    if can_buy: trade_action = "BUY"
    elif can_sell: trade_action = "SELL"

    # --- 3. EXECUTION & LOGGING ---
    if trade_action != "WAITING":
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_trade = pd.DataFrame([[ts, asset.upper(), trade_action, float(current_price), WAGER_SIZE, "OPEN", 0.0]], 
                                   columns=['timestamp','asset','type','price','wager', 'result','profit_usd'])
        
        file_exists = os.path.exists('trades.csv')
        new_trade.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')
        return 0.0, 0.0, trade_action, WAGER_SIZE

    return 0.0, 0.0, "HOLD", WAGER_SIZE
