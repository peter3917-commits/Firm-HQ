import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Aggressively finds columns even if the CSV format is messy."""
    # Default state if file is missing or broken
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL, 
        "tax_pot": 0.0, 
        "trades_df": pd.DataFrame()
    }
    
    if not os.path.exists('trades.csv'):
        return default_data
    
    try:
        df = pd.read_csv('trades.csv')
        
        # 1. FIX THE LEADING COMMA / UNNAMED BUG
        # We drop any column that doesn't have a real name or contains 'Unnamed'
        valid_cols = [c for c in df.columns if 'Unnamed' not in str(c) and c != ""]
        df = df[valid_cols]
        
        # 2. FORCE LOWERCASE FOR LOGIC
        df.columns = [c.lower().strip() for c in df.columns]
        
        # 3. VERIFY ESSENTIAL DATA EXISTS
        if 'result' not in df.columns or 'profit_usd' not in df.columns:
            return default_data

        # 4. CALCULATE TOTALS
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        # Ensure profit_usd is numeric
        df['profit_usd'] = pd.to_numeric(df['profit_usd'], errors='coerce').fillna(0)
        
        realized = df[df['result'].isin(win_labels + ['LOSS', 'LEGACY_CLEANUP'])]['profit_usd'].sum()
        tax_pot = df[df['result'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT
        vault_cash = INITIAL_CAPITAL + realized
        
        return {
            "vault_cash": vault_cash,
            "tradable_balance": vault_cash - tax_pot,
            "tax_pot": tax_pot,
            "trades_df": df
        }
    except Exception as e:
        print(f"CRITICAL LEDGER ERROR: {e}")
        return default_data

def calculate_unrealized(trades_df, prices_dict):
    """Maps BTC to Bitcoin safely."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    unreal_total = 0.0
    
    # Work only on OPEN trades
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = row.get('asset', 'UNKNOWN')
        # Try finding live price by symbol or full name
        live_p = prices_dict.get(asset) or prices_dict.get(mapping.get(asset))
        
        entry_p = pd.to_numeric(row.get('price'), errors='coerce')
        wager = pd.to_numeric(row.get('wager'), errors='coerce')
        
        if live_p and entry_p and entry_p > 0:
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
            
    return unreal_total, open_trades
