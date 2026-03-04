import pandas as pd

def check_for_snap(asset, current_price, history_df):
    """Arthur: Only flags a snap if it exceeds 2%."""
    if history_df.empty or "price_usd" not in history_df.columns:
        return None, 0.0

    # Calculate 48h Average
    moving_avg = history_df['price_usd'].mean()
    
    # Calculate Snap Percentage
    snap_pct = ((current_price - moving_avg) / moving_avg) * 100
    
    # Arthur's new 'High-Conviction' threshold
    if abs(snap_pct) >= 2.0:
        print(f"🏛️ ARTHUR: MAJOR SNAP DETECTED! {snap_pct:.2f}%")
    
    return moving_avg, snap_pct
