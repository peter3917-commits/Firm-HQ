import pandas as pd
import os
from datetime import datetime

def execute_trade(asset, current_price, average, rsi=None, hook_detected=False):
    """
    Lawrence 2.0: High-Volatility Execution Specialist.
    Logic: 2% Snap Trigger | 0.5% Stop-Loss | 50% Target Win Rate.
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
            # For BUY: (Price - Entry) | For SELL: (Entry - Price)
            diff_pct = ((current_price - entry_price) / entry_price) * 100
            if trade_type == "SELL": diff_pct = -diff_pct
            
            # CHECK FOR WIN: Price has returned to the 48h Average (Magnet)
            # We use a small 0.1% buffer to ensure the trade closes smoothly
            hit_magnet = (trade_type == "BUY" and current_price >= average) or \
                         (trade_type == "SELL" and current_price <= average)

            if hit_magnet:
                result = "WIN"
                profit = WAGER_SIZE * (abs(current_price - entry_price) / entry_price)
                df.at[idx, 'result'] = "WIN"
                df.at[idx, 'profit_usd'] = profit
                df.to_csv('trades.csv', index=False)
                return profit, profit, "WIN", WAGER_SIZE

            # CHECK FOR LOSS: Price hit the 0.5% Shield
            elif diff_pct <= -STOP_LOSS_PCT:
                result = "LOSS"
                profit = -(WAGER_SIZE * (STOP_LOSS_PCT / 100))
                df.at[idx, 'result'] = "LOSS"
                df.at[idx, 'profit_usd'] = profit
                df.to_csv('trades.csv', index=False)
                return profit, profit, "LOSS", WAGER_SIZE
            
            # STILL OPEN: Calculate floating P/L for the dashboard
            else:
                floating_pl = WAGER_SIZE * (diff_pct / 100)
                return 0.0, floating_pl, "OPEN", WAGER_SIZE

    # --- 2. NEW TRADE ANALYSIS (THE JURY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Criteria for a BUY:
    # 1. Price is 2% below average
    # 2. Arthur sees a 'Hook' (Price turned up)
    # 3. RSI is below 35 (Oversold condition)
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and hook_detected and (rsi is not None and rsi < 35)
    
    # Criteria for a SELL:
    # 1. Price is 2% above average
    # 2. Arthur sees a 'Hook' (Price turned down)
    # 3. RSI is above 65 (Overbought condition)
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
