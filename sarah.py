import pandas as pd
from data_handler import load_vault, update_vault

def report_trade(asset, trade_type, entry_price, exit_price, amount, p_l, new_bal):
    # 1. Load the current data from Google Sheets
    df = load_vault()

    # 2. Prepare the new row
    new_data = {
        'Staff': 'Sarah',
        'Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Asset': asset,
        'Type': trade_type,
        'Entry': entry_price,
        'Exit': exit_price,
        'P_L': p_l,
        'Balance': new_bal
    }

    # 3. Add to the dataframe and push back to the cloud
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    update_vault(df)
    print(f"Sarah: Trade recorded in Google Sheets. New Balance: ${new_bal:.2f}")