import pandas as pd
import numpy as np

def calculate_rsi(prices, period=100):
    """
    Arthur's Institutional RSI.
    Hardened against NaN and flat-line data.
    """
    if len(prices) < period + 1:
        return 50.0 
    
    delta = pd.Series(prices).diff()
    
    # Simple Moving Average version for smoother 2026-style signals
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # 🛡️ Safety Shield: Handle flat markets where loss is 0.0
    loss = loss.replace(0, np.nan)
    rs = gain / loss
    
    rsi = 100 - (100 / (1 + rs))
    
    val = rsi.iloc[-1]
    # Final check: If calculation fails, return Neutral 50
    return float(val) if not np.isnan(val) else 50.0

def check_for_snap(asset, current_price, history_df, target_snap=1.5, target_rsi=35.0):
    """
    Arthur 2.1: The Asset-Aware Analyst.
    Now accepts custom targets per sector to handle BTC vs. Alts.
    """
    
    # --- DATA INTEGRITY CHECK ---
    price_col = 'Balance' if 'Balance' in history_df.columns else 'price_usd'
    
    if history_df.empty or price_col not in history_df.columns or len(history_df) < 5:
        return None, 0.0, 50.0, False

    # 1. THE MAGNET (24h Moving Average)
    # 288 pings = 24 hours at 5-min intervals
    moving_avg = history_df[price_col].tail(288).mean()
    
    if not moving_avg or moving_avg == 0:
        return None, 0.0, 50.0, False
    
    # 2. THE SNAP (Percentage distance from Mean)
    snap_pct = ((current_price - moving_avg) / moving_avg) * 100
    
    # 3. THE FATIGUE (Smoothing out the 100-period RSI)
    rsi_value = calculate_rsi(history_df[price_col], period=100)
    
    # 4. THE PATIENCE (Hook Detection)
    # Check if we've stopped bleeding relative to the last known data point
    last_recorded_price = history_df[price_col].iloc[-1]
    hook_detected = current_price > last_recorded_price

    # --- ARTHUR'S CONSOLE REPORT ---
    # Now uses the dynamic targets passed from main.py
    if abs(snap_pct) >= target_snap and rsi_value < target_rsi:
        status = "HOOKED 🪝" if hook_detected else "FALLING 🔪"
        # Log to terminal for the engineering team
        print(f"🏛️ ARTHUR AUDIT [{asset}]: Snap: {snap_pct:.2f}% (Goal: {target_snap}%) | RSI: {rsi_value:.1f} | {status}")
    
    return moving_avg, snap_pct, rsi_value, hook_detected
