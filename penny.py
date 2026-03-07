import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
EXCHANGE_FEE_PCT = 0.001
SLIPPAGE_PCT = 0.0005
PROFIT_TAX_PCT = 0.20

def cleanup_legacy_trades(trades_df, prices_dict):
    """Penny's Housekeeping: Standardizes columns and enforces rules."""
    if trades_df.empty:
        return trades_df

    try:
        # 1. Clean Columns
        unnamed_cols = [c for c in trades_df.columns if 'Unnamed' in c]
        if unnamed_cols:
            trades_df = trades_df.drop(columns=unnamed_cols)
        
        trades_df.columns = [c.lower().strip() for c in trades_df.columns]
        
        # 2. Force Data Types
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
        trades_df['wager'] = pd.to_numeric(trades_df['wager'], errors='coerce')
        trades_df['profit_usd'] = pd.to_numeric(trades_df['profit_usd'], errors='coerce')

        # 3. Duplicate Prevention (One OPEN trade per asset)
        open_mask = trades_df['result'] == 'OPEN'
        assets_with_open = trades_df[open_mask]['asset'].unique()

        for asset in assets_with_open:
            asset_mask = (trades_df['asset'] == asset) & (trades_df['result'] == 'OPEN')
            positions = trades_df[asset_mask].sort_values(by='timestamp', ascending=False)

            if len(positions) > 1:
                # Keep newest, close others as LEGACY
                legacy_indices = positions.index[1:]
                for idx in legacy_indices:
                    trades_df.at[idx, 'result'] = 'LEGACY_CLEANUP'
                    
    except Exception as e:
        print(f"⚠️ PENNY CLEANUP ERROR: {e}")

    return trades_df

def get_firm_ledger(prices_dict=None):
    if not os.path.exists('trades.csv'):
        return None
    
    try:
        trades_df = pd.read_csv('trades.csv')
        trades_df = cleanup_legacy_trades(trades_df, prices_dict or {})
        
        # Save back cleaned version
        trades_df.to_csv('trades.csv', index=False)

        # Financial Calculations
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        closed_trades = trades_df[trades_df['result'].isin(win_labels + ['LOSS', 'LEGACY_CLEANUP'])]
        
        gross_realized = closed_trades['profit_usd'].sum()
        total_vol = trades_df['wager'].sum()
        friction = total_vol * (EXCHANGE_FEE_PCT + SLIPPAGE_PCT)
        
        burn_total = 0.0
        if os.path.exists('overheads.csv'):
            burn_total = abs(pd.read_csv('overheads.csv')['amount'].sum())

        tax_pot = trades_df[trades_df['result'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT
        vault_cash = INITIAL_CAPITAL + gross_realized - friction - burn_total
        
        return {
            "vault_cash": vault_cash,
            "tradable_balance": vault_cash - tax_pot,
            "tax_pot": tax_pot,
            "trades_df": trades_df
        }
    except Exception as e:
        print(f"⚠️ LEDGER ERROR: {e}")
        return None

def calculate_unrealized(trades_df, prices_dict):
    """Penny's live P/L tracker. Armored against Symbol/Name mismatches."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    unrealized_total = 0.0
    # Map symbols to full names just in case
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        raw_asset = row['asset']
        # Try finding by raw name, then by mapped name
        current_p = prices_dict.get(raw_asset) or prices_dict.get(mapping.get(raw_asset))
        
        if current_p:
            perf = ((current_p - row['price']) / row['price'])
            pnl = row['wager'] * perf
            unrealized_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl # Update for the table
            
    return unrealized_total, open_trades

def format_terminal_table(df):
    """Formats the dataframe for a professional Streamlit appearance."""
    if df.empty: return df
    
    formatted = df.copy()
    # Rename for the UI
    formatted = formatted.rename(columns={
        'timestamp': 'Date',
        'asset': 'Ticker',
        'price': 'Entry $',
        'wager': 'Capital',
        'result': 'Status',
        'profit_usd': 'P/L £'
    })
    
    # Clean up Date
    formatted['Date'] = pd.to_datetime(formatted['Date']).dt.strftime('%H:%M:%S (%d %b)')
    
    return formatted[['Date', 'Ticker', 'type', 'Status', 'Entry $', 'Capital', 'P/L £']]
