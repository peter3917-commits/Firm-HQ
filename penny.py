import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
EXCHANGE_FEE_PCT = 0.001  # 0.1% per trade
SLIPPAGE_PCT = 0.0005     # 0.05% slippage
MONTHLY_VPS_COST = 15.00
MONTHLY_DATA_COST = 10.00
PROFIT_TAX_PCT = 0.20     # 20% Reserve on Wins

def cleanup_legacy_trades(trades_df, prices_dict):
    """
    Penny's Housekeeping: Standardizes the ledger and enforces the one-asset rule.
    """
    if trades_df.empty:
        return trades_df

    # Force standardization to lowercase to match the Sentinel's expectations
    trades_df.columns = [c.lower().strip() for c in trades_df.columns]
    
    # Ensure timestamp is datetime for sorting
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    
    open_mask = trades_df['result'] == 'OPEN'
    assets_with_open_trades = trades_df[open_mask]['asset'].unique()

    for asset in assets_with_open_trades:
        asset_mask = (trades_df['asset'] == asset) & (trades_df['result'] == 'OPEN')
        open_positions = trades_df[asset_mask]

        if len(open_positions) > 1:
            # Sort: Newest at the top
            open_positions = open_positions.sort_values(by='timestamp', ascending=False)
            
            # Keep the newest index, target the rest for cleanup
            legacy_indices = open_positions.index[1:]
            current_price = prices_dict.get(asset) if prices_dict else None
            
            for idx in legacy_indices:
                entry = trades_df.at[idx, 'price']
                wager = trades_df.at[idx, 'wager']
                
                # Calculate P/L to keep the Vault balance honest
                if current_price:
                    exit_price = current_price * 0.9999
                    pnl = ((exit_price - entry) / entry) * wager
                else:
                    pnl = 0.0 
                
                trades_df.at[idx, 'result'] = 'LEGACY_CLEANUP'
                trades_df.at[idx, 'profit_usd'] = pnl
                print(f"🧹 PENNY: Removing ghost trade {asset} from {trades_df.at[idx, 'timestamp']}")

    return trades_df

def get_firm_ledger(prices_dict=None):
    """Penny's core logic: Calculates Firm state and cleans the ledger."""
    if not os.path.exists('trades.csv'):
        return None
    
    trades_df = pd.read_csv('trades.csv')
    
    # 1. Housekeeping (Crucial to restore Sentinel view)
    trades_df = cleanup_legacy_trades(trades_df, prices_dict)
    trades_df.to_csv('trades.csv', index=False)

    # 2. Realized Totals
    win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
    all_closed_labels = win_labels + ['LOSS', 'LEGACY_CLEANUP']
    
    closed_trades = trades_df[trades_df['result'].isin(all_closed_labels)].copy()
    gross_realized = closed_trades['profit_usd'].sum()
    
    # 3. Friction & Burn
    total_volume = trades_df['wager'].sum() 
    friction = total_volume * (EXCHANGE_FEE_PCT + SLIPPAGE_PCT)
    
    burn_total = 0.0
    if not os.path.exists('overheads.csv'):
        burn_df = pd.DataFrame([{"date": datetime.now().strftime('%Y-%m-%d'), "amount": -(MONTHLY_VPS_COST + MONTHLY_DATA_COST)}])
        burn_df.to_csv('overheads.csv', index=False)
        burn_total = (MONTHLY_VPS_COST + MONTHLY_DATA_COST)
    else:
        burn_df = pd.read_csv('overheads.csv')
        burn_total = abs(burn_df['amount'].sum())

    # 4. Tax & Vault
    wins = trades_df[trades_df['result'].isin(win_labels)]
    tax_pot = wins['profit_usd'].sum() * PROFIT_TAX_PCT
    vault_cash = INITIAL_CAPITAL + gross_realized - friction - burn_total
    tradable_balance = vault_cash - tax_pot
    
    # --- LIVE CONSOLE REPORT ---
    print("\n" + "🏛️  ACCOUNTANT'S AUDIT COMPLETE")
    print(f"Vault: ${vault_cash:,.2f} | Tradable: ${tradable_balance:,.2f}")
    print(f"Cleaned {len(trades_df[trades_df['result'] == 'LEGACY_CLEANUP'])} ghost trades.\n")

    return {
        "vault_cash": vault_cash,
        "tradable_balance": tradable_balance,
        "tax_pot": tax_pot,
        "friction": friction,
        "burn": burn_total,
        "gross_realized": gross_realized,
        "trades_df": trades_df
    }

def calculate_unrealized(trades_df, prices_dict):
    """Calculates floating P/L for the Sentinel's active view."""
    # Ensure lowercase 'asset' for compatibility
    trades_df.columns = [c.lower().strip() for c in trades_df.columns]
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    unrealized_pl = 0.0
    
    if open_trades.empty:
        return 0.0, open_trades

    for idx, row in open_trades.iterrows():
        asset = row['asset']
        current_price = prices_dict.get(asset)
        if current_price:
            bid_price = current_price * 0.9999 
            diff = ((bid_price - row['price']) / row['price']) * row['wager']
            unrealized_pl += diff
            open_trades.at[idx, 'floating_pl'] = diff
        
    return unrealized_pl, open_trades
