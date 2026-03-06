import pandas as pd
import os
from datetime import datetime

def execute_trade(asset, current_price, average, rsi=None, prev_price=None):
    """
    Lawrence 2.2: Multi-Asset Spread-Aware Execution.
    Ensures each asset is tracked independently in the ledger.
    """
    
    # --- INSTITUTIONAL SPREAD SIMULATION ---
    ask_price = current_price * 1.0001  # Price you pay to BUY
    bid_price = current_price * 0.9999  # Price you get when you SELL
    
    # --- CAPITAL MANAGEMENT ---
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 # Strict 10% per trade
    
    # --- STRATEGY SETTINGS ---
    TRIGGER_THRESHOLD = 2.0  # 2% Gap from Magnet
    STOP_LOSS_PCT = 0.5      # 0.5% Shield
    
    # Default outputs
    profit = 0.0
    result = "HOLD"

    # --- SAFETY CHECK ---
    if not current_price or not average or average == 0:
        return 0.0, 0.0, "WAITING", WAGER_SIZE

    # --- 1. ACTIVE TRADE MONITORING (Asset Specific) ---
    if os.path.exists('trades.csv'):
        df = pd.read_csv('trades.csv')
        if not df.empty:
            # 🛡️ THE NORMALIZATION SHIELD: Fixes the KeyError in GitHub Actions
            # This converts 'asset' -> 'Asset' automatically if the CSV is old.
            df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]

            # 🛡️ This line will now work perfectly even if the file had lowercase 'asset'
            mask = (df['result'] == 'OPEN') & (df['Asset'] == asset)
            
            if mask.any():
                idx = df[mask].index[-1]
                entry_price = df.at[idx, 'price']
                trade_type = df.at[idx, 'type']
                
                if trade_type == "BUY":
                    current_performance_pct = ((bid_price - entry_price) / entry_price) * 100
                    hit_magnet = (bid_price >= average)
                else: # SELL/SHORT
                    current_performance_pct = ((entry_price - ask_price) / entry_price) * 100
                    hit_magnet = (ask_price <= average)

                # Check for Exit Signals
                if hit_magnet:
                    result = "WIN"
                    profit = WAGER_SIZE * (current_performance_pct / 100)
                    df.at[idx, 'result'] = "WIN"
                    df.at[idx, 'profit_usd'] = profit
                    df.to_csv('trades.csv', index=False)
                    return profit, profit, "WIN", WAGER_SIZE

                elif current_performance_pct <= -STOP_LOSS_PCT:
                    result = "LOSS"
                    profit = WAGER_SIZE * (current_performance_pct / 100)
                    df.at[idx, 'result'] = "LOSS"
                    df.at[idx, 'profit_usd'] = profit
                    df.to_csv('trades.csv', index=False)
                    return profit, profit, "LOSS", WAGER_SIZE
                
                else:
                    floating_pl = WAGER_SIZE * (current_performance_pct / 100)
                    return 0.0, floating_pl, "OPEN", WAGER_SIZE

    # --- 2. NEW TRADE ANALYSIS ---
    snap_pct = ((current_price - average) / average) * 100
    
    hook_detected = False
    if prev_price is not None and current_price > prev_price:
        hook_detected = True
    
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and hook_detected and (rsi is not None and rsi < 35)
    can_sell = (snap_pct >= TRIGGER_THRESHOLD) and (not hook_detected) and (rsi is not None and rsi > 65)

    trade_action = "WAITING"
    if can_buy: trade_action = "BUY"
    elif can_sell: trade_action = "SELL"

    # --- 3. EXECUTION & LOGGING ---
    if trade_action != "WAITING":
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_price = ask_price if trade_action == "BUY" else bid_price
        
        # 🛡️ Ensuring NEW trades always use Capital 'Asset'
        new_trade = pd.DataFrame([[ts, asset, trade_action, float(execution_price), WAGER_SIZE, "OPEN", 0.0]], 
                                   columns=['timestamp','Asset','type','price','wager', 'result','profit_usd'])
        
        file_exists = os.path.exists('trades.csv')
        new_trade.to_csv('trades.csv', mode='a', header=not file_exists, index=False, lineterminator='\n')
        return 0.0, 0.0, trade_action, WAGER_SIZE

    return 0.0, 0.0, "HOLD", WAGER_SIZE
