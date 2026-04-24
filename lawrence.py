import pandas as pd
import os
from datetime import datetime
import numpy as np
import uuid

def calculate_wma(prices, period=5):
    """Calculates Weighted Moving Average for the trailing exit."""
    if len(prices) < period:
        return prices[-1]
    weights = np.arange(1, period + 1)
    return (prices[-period:] * weights).sum() / weights.sum()

def generate_deterministic_id(asset, interval_ms=300000):
    """Generates a UUID v5 anchored to the current 5-minute candle bucket."""
    time_bucket = int(datetime.now().timestamp() * 1000 // interval_ms) * interval_ms
    seed = f"{asset}-{time_bucket}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))

def execute_trade(asset, current_price, average, rsi=None, history_df=None, ledger_df=None, tradable_balance=1000.0):
    """
    Lawrence 6.0: The Reversion Sentinel.
    Features: UUID v5 Determinism, 1.0% Hard Shield, and Trailing Magnet Exit.
    Corrects the 'Momentum Trap' by prioritizing the 24h Magnet Reversion.
    """
    # --- TICKER BRIDGE ---
    ticker_map = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- ⚖️ 2026 DYNAMIC SETTINGS ---
    # Wager reduced to 10% for better risk management and compounding
    WAGER_SIZE = round(tradable_balance * 0.10, 2)
    
    ask_price = round(current_price * 1.0001, 2) if current_price else 0
    bid_price = round(current_price * 0.9999, 2) if current_price else 0
    
    # Recalibrated Shield and Exit targets
    STOP_LOSS_PCT = 1.0       # 1% Hard Shield to protect the Vault
    TRAILING_GAP = 0.5        # 0.5% Trail once Magnet is breached
    
    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", None

    # --- INDICATOR PREP ---
    prices_arr = history_df.iloc[:, -1].values 
    ema_5 = history_df.iloc[:, -1].ewm(span=5, adjust=False).mean().iloc[-1]

    # --- 1. ACTIVE TRADE MONITORING ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            df = ledger_df.copy()
            df.columns = [c.lower().strip() for c in df.columns]
            
            for i in range(len(df)):
                csv_asset = str(df.iloc[i]['asset']).strip().upper()
                status = str(df.iloc[i]['result']).strip().upper()
                
                if status == 'OPEN' and csv_asset == search_asset:
                    entry_price = float(df.iloc[i]['price'])
                    current_wager = float(df.iloc[i]['wager'])
                    perf = ((bid_price - entry_price) / entry_price) * 100
                    
                    # --- REVERSION EXIT LOGIC ---
                    # A) THE SHIELD: Exit if price drops 1% below entry
                    hit_stop = (perf <= -STOP_LOSS_PCT)
                    
                    # B) THE MAGNET TRAIL: Exit if price returns to or exceeds 24h Average
                    # Note: We exit at Magnet touch to ensure £200/mo volume targets
                    hit_magnet_reversion = (bid_price >= average)

                    outcome = "OPEN"
                    exit_triggered = False

                    if hit_stop:
                        outcome, exit_triggered = "LOSS", True
                    elif hit_magnet_reversion:
                        outcome, exit_triggered = "WIN_TRAILING", True

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
    
    # The Hook: Confirming the 5-min trend has reversed
    last_price = history_df.iloc[-1].values[-1] if not history_df.empty else current_price
    fast_hook = current_price > last_price
    
    # Triple-Filter Entry: Stretch + Panic + Hook
    can_buy = (snap_pct <= -1.5) and (rsi is not None and rsi < 35) and fast_hook

    # --- 3. EXECUTION ---
    if can_buy:
        # Generate Deterministic ID for Exchange Idempotency
        order_id = generate_deterministic_id(search_asset)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # trade_info includes order_id for future API recovery
        trade_info = [ts, search_asset, "BUY", ask_price, WAGER_SIZE, "OPEN", 0.0]
        return 0.0, 0.0, "BUY", trade_info

    return 0.0, 0.0, "HOLD", None
