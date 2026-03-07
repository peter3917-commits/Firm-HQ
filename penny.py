import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
EXCHANGE_FEE_PCT = 0.001
SLIPPAGE_PCT = 0.0005
MONTHLY_VPS_COST = 15.00
MONTHLY_DATA_COST = 10.00
PROFIT_TAX_PCT = 0.20

def cleanup_legacy_trades(trades_df, prices_dict):
    """Penny's Housekeeping: Standardizes columns and enforces the one-asset rule."""
    if trades_df.empty:
        return trades_df

    try:
        # 1. DROP UNWANTED INDEX COLUMNS
        unnamed_cols = [c for c in trades_df.columns if 'Unnamed' in c]
        if unnamed_cols:
            trades_df = trades_df.drop(columns=unnamed_cols)
        
        # 2. FORCE STANDARDIZED LOWERCASE
        trades_df.columns = [c.lower().strip() for c in trades_df.columns]
        
        # 3. ENSURE ALL REQUIRED COLUMNS EXIST
        required = ['timestamp', 'asset', 'type', 'price', 'wager', 'result', 'profit_usd']
        for col in required:
            if col not in trades_df.columns:
                trades_df[col] = 0 if col in ['price', 'wager', 'profit_usd'] else "UNKNOWN"

        # 4. EXECUTE CLEANUP
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        open_mask = trades_df['result'] == 'OPEN'
        assets_with_open_trades = trades_df[open_mask]['asset'].unique()

        for asset in assets_with_open_trades:
            asset_mask = (trades_df['asset'] == asset) & (trades_df['result'] == 'OPEN')
            open_positions = trades_df[asset_mask].sort_values(by='timestamp', ascending=False)

            if len(open_positions) > 1:
                legacy_indices = open_positions.index[1:]
                
                # Mapping symbols to names
                current_price = prices_dict.get(asset) 
                if not current_price and asset == "BTC": current_price = prices_dict.get("Bitcoin")
                if not current_price and asset == "ETH": current_price = prices_dict.get("Ethereum")
                if not current_price and asset == "SOL": current_price = prices_dict.get("Solana")
                
                for idx in legacy_indices:
                    entry = trades_df.at[idx, 'price']
                    wager = trades_df.at[idx, 'wager']
                    
                    if current_price:
                        exit_price = current_price * 0.9999
                        pnl = ((exit_price - entry) / entry) * wager
                    else:
                        pnl = 0.0 
                    
                    trades_df.at[idx, 'result'] = 'LEGACY_CLEANUP'
                    trades_df.at[idx, 'profit_usd'] = pnl
    except Exception as e:
        print(f"⚠️ PENNY ERROR DURING CLEANUP: {e}")

    return trades_df

def get_firm_ledger(prices_dict=None):
    """The master ledger logic. Hardened against CSV corruption."""
    if not os.path.exists('trades.csv'):
        return None
    
    try:
        trades_df = pd.read_csv('trades.csv')
        trades_df = cleanup_legacy_trades(trades_df, prices_dict or {})
        
        try:
            trades_df.to_csv('trades.csv', index=False)
        except:
            pass 

        # Calculate Totals
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        all_closed = win_labels + ['LOSS', 'LEGACY_CLEANUP']
        
        closed_trades = trades_df[trades_df['result'].isin(all_closed)]
        gross_realized = closed_trades['profit_usd'].sum()
        
        total_volume = trades_df['wager'].sum() 
        friction = total_volume * (EXCHANGE_FEE_PCT + SLIPPAGE_PCT)
        
        burn_total = 0.0
        if os.path.exists('overheads.csv'):
            try:
                burn_df = pd.read_csv('overheads.csv')
                burn_total = abs(burn_df['amount'].sum())
            except:
                pass

        wins = trades_df[trades_df['result'].isin(win_labels)]
        tax_pot = wins['profit_usd'].sum() * PROFIT_TAX_PCT
        vault_cash = INITIAL_CAPITAL + gross_realized - friction - burn_total
        tradable_balance = vault_cash - tax_pot
        
        return {
            "vault_cash": vault_cash,
            "tradable_balance": tradable_balance,
            "tax_pot": tax_pot,
            "friction": friction,
            "burn": burn_total,
            "trades_df": trades_df
        }
    except Exception as e:
        print(f"⚠️ LEDGER ERROR: {e}")
        return None

def calculate_unrealized(trades_df, prices_dict):
    """Penny's quick check on floating P/L."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    unrealized_total = 0.0
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = row['asset']
        current_price = prices_dict.get(asset)
        if not current_price and asset == "Bitcoin": current_price = prices_dict.get("Bitcoin")
        
        if current_price:
            perf = ((current_price - row['price']) / row['price'])
            unrealized_total += (row['wager'] * perf)
            
    return unrealized_total, open_trades
