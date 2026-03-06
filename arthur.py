import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    """Arthur's sense of 'Overstretched' markets using RSI logic."""
    if len(prices) < period + 1:
        return 50.0  # Neutral starting point
    
    delta = pd.Series(prices).diff()
    # Simple Moving Average version of RSI for smoother signals
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Replace zeros to prevent division errors
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    # Return the latest value, handle NaN by returning neutral 50
    val = rsi.iloc[-1]
    return float(val) if not np.isnan(val) else 50.0

def check_for_snap(asset, current_price, history_df):
    """
    Arthur 2.0: The Market Analyst.
    Returns: (moving_avg, snap_pct, rsi_value, hook_detected)
    """
    
    # Identify the correct column from George's data
    price_col = 'Balance' if 'Balance' in history_df.columns else 'price_usd'
    
    # Safety Check: If no data, return neutral values to prevent crash
    if history_df.empty or price_col not in history_df.columns:
        return None, 0.0, 50.0, False

    # 1. THE MAGNET (48h Moving Average)
    # 48 hours * 12 pings/hour (5-min intervals) = 576 data points
    moving_avg = history_df[price_col].tail(576).mean()
    
    # 2. THE SNAP (Distance from Magnet)
    snap_pct = ((current_price - moving_avg) / moving_avg) * 100
    
    # 3. THE FATIGUE (RSI Calculation)
    rsi_value = calculate_rsi(history_df[price_col])
    
    # 4. THE PATIENCE (The Hook Detection)
    # Arthur looks at the previous 5-minute price to see if the bleeding stopped
    last_recorded_price = history_df[price_col].iloc[-1]
    hook_detected = current_price > last_recorded_price

    # --- ARTHUR'S CONSOLE REPORT ---
    # He only speaks up when things get interesting (2% threshold)
    if abs(snap_pct) >= 2.0:
        status = "HOOKED 🪝" if hook_detected else "FALLING 🔪"
        print(f"🏛️ ARTHUR: {asset} is {snap_pct:.2f}% from Magnet | RSI: {rsi_value:.1f} | {status}")
    
    return moving_avg, snap_pct, rsi_value, hook_detected
