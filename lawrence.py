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

def execute_trade(asset, current_price, average, rsi=None, history_df=None, ledger_df=None, tradable_balance=1000.0):
    """
    Lawrence 5.0: Dynamic Institutional Execution.
    Now implements 20% Compound Waging and Hardened State Tracking.
    """
    # --- TICKER BRIDGE ---
    ticker_map = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- ⚖️ 2026 DYNAMIC SETTINGS ---
    # Jace Logic: Use 20% of whatever Penny says is in the 'Tradable' pot
    WAGER_SIZE = round(tradable_balance * 0.20, 2)
    
    # Slippage adjustment for institutional bid/ask
    ask_price = round(current_price * 1.0001, 2) if current_price else 0
    bid_price = round(current_price * 0.9999, 2) if current_price else 0
    
    STOP_LOSS_PCT = 3.5      
    TARGET_OVER_MAGNET = 10.0 
    
    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", None

    # --- INDICATOR PREP ---
    prices_arr = history_df.iloc[:, -1].values # Robust column selection
    ema_5 = history_df.iloc[:, -1].ewm(span=5, adjust=False).mean().iloc[-1]
    wma_5 = calculate_wma(prices_arr, period=5)

    # --- 1. ACTIVE TRADE MONITORING ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            df = ledger_df.copy()
            df.columns = [c.lower().strip() for c in df.columns]
            
            for i in range(len(df)):
                csv_asset = str(df.iloc[i]['asset']).strip().upper()
                # Clean check for "OPEN" status
                status = str(df.iloc[i]['result']).strip().upper()
                
                if status == 'OPEN' and csv_asset == search_asset:
                    entry_price = float(df.iloc[i]['price'])
                    current_wager = float(df.iloc[i]['wager'])
                    perf = ((bid_price - entry_price) / entry_price) * 100
                    
                    # Exit Conditions
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
                        pnl_val = round(current_wager * (perf / 100), 2)
                        trade_update = {
                            "index": i,
                            "result": outcome,
                            "profit_usd": pnl_val
                        }
                        return pnl_val, pnl_val, outcome, trade_update
                    
                    return 0.0, round(current_wager * (perf / 100), 2), "OPEN", None
        except Exception as e:
            print(f"🏛️ LAWRENCE ERROR: Ledger corruption detected at row {i}. Skipping...")

    # --- 2. NEW TRADE ANALYSIS ---
    snap_pct = ((current_price - average) / average) * 100
    fast_hook = current_price > ema_5
    
    # Threshold check (Defaulting to 1.5% snap and 35 RSI unless main.py overrides)
    can_buy = (snap_pct <= -1.5) and fast_hook and (rsi is not None and rsi < 35)

    # --- 3. EXECUTION ---
    if can_buy:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Format: timestamp, asset, type, price, wager, result, profit_usd
        trade_info = [ts, search_asset, "BUY", ask_price, WAGER_SIZE, "OPEN", 0.0]
        return 0.0, 0.0, "BUY", trade_info

    return 0.0, 0.0, "HOLD", None
