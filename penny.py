import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Guaranteed return of a dictionary, even if the file is missing or corrupted."""
    default = {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "trades_df": pd.DataFrame()}
    
    if not os.path.exists('trades.csv'):
        return default
    
    try:
        df = pd.read_csv('trades.csv')
        
        # --- DEFENSE 1: KILL THE LEADING COMMA BUG ---
        unnamed = [c for c in df.columns if 'Unnamed' in c or c == ""]
        if unnamed:
            df = df.drop(columns=unnamed)
        
        # Standardize for logic
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Financials
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        realized = df[df['result'].isin(win_labels + ['LOSS', 'LEGACY_CLEANUP'])]['profit_usd'].sum()
        tax_pot = df[df['result'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT
        
        return {
            "vault_cash": INITIAL_CAPITAL + realized,
            "tradable_balance": (INITIAL_CAPITAL + realized) - tax_pot,
            "tax_pot": tax_pot,
            "trades_df": df
        }
    except Exception as e:
        print(f"Defensive Ledger Catch: {e}")
        return default

def calculate_unrealized(trades_df, prices_dict):
    """Defense 2: BTC -> Bitcoin Translation."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    unreal_total = 0.0
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = row['asset']
        # Check 'BTC' then 'Bitcoin'
        price = prices_dict.get(asset) or prices_dict.get(mapping.get(asset))
        
        if price and row['price'] > 0:
            pnl = row['wager'] * ((price - row['price']) / row['price'])
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
            
    return unreal_total, open_trades
