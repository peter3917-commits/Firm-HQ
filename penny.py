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

def get_firm_ledger():
    """Penny's core logic: Calculates the true state of the Firm."""
    if not os.path.exists('trades.csv'):
        return None
    
    trades_df = pd.read_csv('trades.csv')
    
    # 1. Calculate Realized Trade Profit
    closed_trades = trades_df[trades_df['result'].isin(['WIN', 'LOSS'])].copy()
    gross_realized = closed_trades['profit_usd'].sum()
    
    # 2. Transactional Friction (Fees + Slippage)
    total_volume = trades_df['wager'].sum() 
    friction = total_volume * (EXCHANGE_FEE_PCT + SLIPPAGE_PCT)
    
    # 3. Operational Burn (Monthly Costs)
    burn_total = 0.0
    if not os.path.exists('overheads.csv'):
        # First-time setup: Log initial monthly costs
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

    # 4. The Tax Pot (Locked Profit)
    wins = trades_df[trades_df['result'] == 'WIN']
    tax_pot = wins['profit_usd'].sum() * PROFIT_TAX_PCT
    
    # 5. Final Calculations
    vault_cash = INITIAL_CAPITAL + gross_realized - friction - burn_total
    tradable_balance = vault_cash - tax_pot
    
    return {
        "vault_cash": vault_cash,
        "tradable_balance": tradable_balance,
        "tax_pot": tax_pot,
        "friction": friction,
        "burn": burn_total,
        "gross_realized": gross_realized,
        "trades_df": trades_df
    }

def calculate_unrealized(trades_df, current_price):
    """
    Calculates the HONEST liquidated value of trades.
    Uses Bid/Ask spread so you see what you'd actually walk away with.
    """
    # 🛡️ THE FIX: SAFETY GUARD
    # If George fails to find a price, we return 0.0 instead of crashing.
    if current_price is None:
        open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
        if not open_trades.empty:
            open_trades['floating_pl'] = 0.0
        return 0.0, open_trades

    # Simulate the exit prices
    bid_price = current_price * 0.9999  # What you get if you SELL
    ask_price = current_price * 1.0001  # What you pay to BUY back
    
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    unrealized_pl = 0.0
    
    for idx, row in open_trades.iterrows():
        entry = row['price']
        wager = row['wager']
        
        if row['type'] == "BUY":
            # If you are long, you must exit at the lower BID price
            diff = ((bid_price - entry) / entry) * wager
        else: 
            # If you are short, you must buy back at the higher ASK price
            diff = ((entry - ask_price) / entry) * wager
            
        unrealized_pl += diff
        open_trades.at[idx, 'floating_pl'] = diff
        
    return unrealized_pl, open_trades
