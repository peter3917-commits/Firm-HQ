import pandas as pd
from data_handler import load_vault, update_vault

def take_taxes_and_overheads():
    df = load_vault()
    if df.empty:
        return

    current_bal = df['Balance'].iloc[-1]
    # Example: $5.00 overhead charge
    cost = 5.00
    new_bal = current_bal - cost

    new_data = {
        'Staff': 'Penny',
        'Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Asset': 'OVERHEAD',
        'Type': 'FEE',
        'Entry': 0,
        'Exit': 0,
        'P_L': -cost,
        'Balance': new_bal
    }

    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    update_vault(df)