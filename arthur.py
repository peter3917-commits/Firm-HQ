import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    """Arthur's sense of 'Overstretched' markets."""
    if len(prices) < period + 1:
        return 50  # Neutral
    
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Avoid division by zero
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def check_for_snap(asset, current_price, history_df):
    """Arthur 2.0: Now monitors Average, RSI, and The Hook."""
    
    # Flexibility check: handle both 'Balance' (from George) and 'price_usd'
    price_col = 'Balance' if 'Balance' in history_df.columns else 'price_usd'
    
    if history_df.empty or price_col not in history_df.columns:
        return None, 0.0, 50, False

    # 1. Calculate 48h Average (The Magnet)
    moving_avg = history_df[price_col].tail(576).mean()
    
    # 2. Calculate Snap Percentage
    snap_pct = ((current_price - moving_avg) / moving_avg) * 100
    
    # 3. Calculate RSI (The Fatigue)
    rsi_value = calculate_rsi(history_df[price_col])
    
    # 4. Detect 'The Hook' (The Patience)
    # We check if the price has ticked UP from the last recorded entry
    last_recorded_price = history_df[price_col].iloc[-1]
    hook_detected = current_price > last_recorded_price

    # Arthur's Intelligence Report
    if abs(snap_pct) >= 2.0:
        status = "HOOKED 🪝" if hook_detected else "FALLING 🔪"
        print(f"🏛️ ARTHUR: {snap_pct:.2f}% Snap | RSI: {rsi_value:.1f} | Status: {status}")
    
    # Return 4 values to the Scout Engine
    return moving_avg, snap_pct, rsi_value, hook_detected
