import pandas as pd
from data_handler import load_vault, update_vault

def report_trade(asset, trade_type, entry_price, exit_price, amount, p_l, new_bal):
    # 1. Load data
    df = load_vault()

    # 2. Prepare row to match your headers exactly
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

    # 3. Append and Update
    new_row = pd.DataFrame([new_data])
    df = pd.concat([df, new_row], ignore_index=True)
    
    update_vault(df)
