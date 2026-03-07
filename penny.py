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
    Penny's Housekeeping: Detects multiple open trades for the same asset.
    It keeps only the NEWEST trade active and closes the rest as 'LEGACY_CLEANUP'.
    """
    if trades_df.empty:
        return trades_df

    # DEFENSIVE: Identify asset column regardless of case
    asset_col = next((c for c in trades_df.columns if c.lower() == 'asset'), 'asset')
    
    open_mask = trades_df['result'] == 'OPEN'
    assets_with_open_trades = trades_df[open_mask][asset_col].unique()

    for asset in assets_with_open_trades:
        asset_mask = (trades_df[asset_col] == asset) & (trades_df['result'] == 'OPEN')
        open_positions = trades_df[asset_mask]

        if len(open_positions) > 1:
            # Sort by timestamp to find the latest one
            open_positions = open_positions.sort_values(by='timestamp', ascending=False)
            latest_idx = open_positions.index[0]
            legacy_indices = open_positions.index[1:]

            current_price = prices_dict.get(asset)
            
            for idx in legacy_indices:
                entry = trades_df.at[idx, 'price']
                wager = trades_df.at[idx, 'wager']
                
                if current_price:
                    exit_price = current_price * 0.9999 # Bid price
                    pnl = ((exit_price - entry) / entry) * wager
                else:
                    pnl = 0.0 
                
                trades_df.at[idx, 'result'] = 'LEGACY_CLEANUP'
                trades_df.at[idx, 'profit_usd'] = pnl
                print(f"🧹 PENNY: Cleaning up legacy {asset} trade from {trades_df.at[idx, 'timestamp']}. P/L: ${pnl:.2f}")

    return trades_df

def get_firm_ledger(prices_dict=None):
    """Penny's core logic: Calculates the true state of the Firm and generates the Institutional Ledger."""
    if not os.path.exists('trades.csv'):
        return None
    
    trades_df = pd.read_csv('trades.csv')
    
    # 0. Standardize to lowercase 'asset' to ensure Sentinel doesn't lose data
    trades_df.columns = [c.lower() if c.lower() == 'asset' else c for c in trades_df.columns]
    
    # 1. Housekeeping (Remove the 7 legacy trades)
    if prices_dict:
        trades_df = cleanup_legacy_trades(trades_df, prices_dict)
        trades_df.to_csv('trades.csv', index=False)

    # 2. Calculate Realized Trade Profit
    win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
    all_closed_labels = win_labels + ['LOSS', 'LEGACY_CLEANUP']
    
    closed_trades = trades_df[trades_df['result'].isin(all_closed_labels)].copy()
    gross_realized = closed_trades['profit_usd'].sum()
    
    # 3. Transactional Friction
    total_volume = trades_df['wager'].sum() 
    friction = total_volume * (EXCHANGE_FEE_PCT + SLIPPAGE_PCT)
    
    # 4. Operational Burn
    burn_total = 0.0
    if not os.path.exists('overheads.csv'):
        burn_df = pd.DataFrame([{
            "date": datetime.now().strftime('%Y-%m-%d'),
            "category": "Fixed",
            "description": "Initial Server/Data Setup",
            "amount": -(MONTHLY_VPS_COST + MONTHLY_DATA_COST)
        }])
        burn_df.to_csv('overheads.csv', index=False)
        burn_total = (MONTHLY_VPS_COST + MONTHLY_DATA_COST)
    else:
        burn_df = pd.read_csv('overheads.csv')
        burn_total = abs(burn_df['amount'].sum())

    # 5. The Tax Pot
    wins = trades_df[trades_df['result'].isin(win_labels)]
    tax_pot = wins['profit_usd'].sum() * PROFIT_TAX_PCT
    
    # 6. Final Calculations
    vault_cash = INITIAL_CAPITAL + gross_realized - friction - burn_total
    tradable_balance = vault_cash - tax_pot
    
    # --- INSTITUTIONAL LEDGER DISPLAY ---
    print("\n" + "="*50)
    print("🏛️  OFFICE OF THE ACCOUNTANT: PROFESSIONAL LEDGER")
    print("="*50)
    
    if prices_dict:
        unrealized_pl, open_df = calculate_unrealized(trades_df, prices_dict)
        if not open_df.empty:
            display_df = open_df.copy()
            display_df['Return %'] = (display_df['floating_pl'] / display_df['wager']) * 100
            # Clean display for the console
            fmt = display_df[['timestamp', 'asset', 'price', 'wager', 'floating_pl', 'Return %']]
            print(fmt.to_string(index=False))
        else:
            print("No active positions.")
    
    print("-" * 50)
    print(f"Vault Cash:        ${vault_cash:,.2f}")
    print(f"Tradable Balance:  ${tradable_balance:,.2f}")
    print(f"Tax Reserve:       ${tax_pot:,.2f}")
    print(f"Total Burn:        ${burn_total:,.2f}")
    print("="*50 + "\n")

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
    """Calculates the HONEST liquidated value of trades across multiple sectors."""
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    unrealized_pl = 0.0
    
    if open_trades.empty:
        return 0.0, open_trades

    asset_col = next((c for c in trades_df.columns if c.lower() == 'asset'), 'asset')

    for idx, row in open_trades.iterrows():
        asset = row.get(asset_col, 'Bitcoin') 
        current_price = prices_dict.get(asset)

        if current_price is None:
            open_trades.at[idx, 'floating_pl'] = 0.0
            continue

        bid_price = current_price * 0.9999 
        entry = row['price']
        wager = row['wager']
        
        diff = ((bid_price - entry) / entry) * wager
            
        unrealized_pl += diff
        open_trades.at[idx, 'floating_pl'] = diff
        
    return unrealized_pl, open_trades
