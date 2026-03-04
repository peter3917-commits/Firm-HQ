import pandas as pd

def check_for_snap(asset, current_price_usd, history_df):
    """
    Arthur calculates the moving average based on George's 48-hour price tape.
    He checks for 'None' values and empty data to prevent firm-wide crashes.
    """
    # SAFETY GATE: If George hasn't delivered a price yet, Arthur stays quiet.
    if current_price_usd is None or history_df is None or history_df.empty:
        return None, 0.0

    try:
        # Calculate the average of the 'price_usd' column.
        # With George's new logic, this average now spans up to 48 hours of data.
        moving_avg = history_df['price_usd'].mean()

        # Another safety check to ensure moving_avg is a valid number
        if pd.isna(moving_avg) or moving_avg == 0:
            return None, 0.0

        # The 'Snap' calculation: 
        # Measuring how far the current price has 'snapped' away from the 48-hour mean.
        diff_pct = ((current_price_usd - moving_avg) / moving_avg) * 100

        return moving_avg, diff_pct

    except Exception:
        # If any calculation error occurs, Arthur reports nothing to avoid false trades.
        return None, 0.0