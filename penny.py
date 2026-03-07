import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
EXCHANGE_FEE_PCT = 0.001
SLIPPAGE_PCT = 0.0005
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Safe Ledger: Returns basic data without complex formatting."""
    if not os.path.exists('trades.csv'):
        return {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "trades_df": pd.DataFrame()}
    
    try:
        df = pd.read_csv('trades.csv')
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Financials
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        realized = df[df['result'].isin(win_labels + ['LOSS', 'LEGACY_CLEANUP'])]['profit_usd'].sum()
        
        tax_pot = df[df['result'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT
        vault_cash = INITIAL_CAPITAL + realized
        
        return {
            "vault_cash": vault_cash,
            "tradable_balance": vault_cash - tax_pot,
            "tax_pot": tax_pot,
            "trades_df": df
        }
    except:
        return {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "trades_df": pd.DataFrame()}

def calculate_unrealized(trades_df, prices_dict):
    """Safe Live P/L calculation."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    unrealized_total = 0.0
    # Mapping to catch "BTC" vs "Bitcoin"
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = row['asset']
        # Try both the name in the CSV and the mapping
        price = prices_dict.get(asset) or prices_dict.get(mapping.get(asset))
        
        if price:
            perf = ((price - row['price']) / row['price'])
            pnl = row['wager'] * perf
            unrealized_total += pnl
            
    return unrealized_total, open_trades
