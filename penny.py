import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Aggressively finds columns and calculates metrics with Zero-Value Insurance."""
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL, 
        "tax_pot": 0.0, 
        "burn": 0.0,
        "trades_df": pd.DataFrame()
    }
    
    if not os.path.exists('trades.csv'):
        return default_data
    
    try:
        # 1. READ AND FIX GHOST COLUMNS (Leading Comma Bug)
        df = pd.read_csv('trades.csv')
        valid_cols = [c for c in df.columns if 'Unnamed' not in str(c) and c != ""]
        df = df[valid_cols]
        
        # 2. SHIELD: FORCE LOWERCASE HEADERS
        df.columns = [c.lower().strip() for c in df.columns]
        
        # 3. DATA CLEANING & FLOAT INSURANCE
        df['profit_usd'] = pd.to_numeric(df['profit_usd'], errors='coerce').fillna(0.0)
        df['wager'] = pd.to_numeric(df['wager'], errors='coerce').fillna(0.0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        
        # 4. EXECUTIVE SUMMARY MATH (Forcing float to prevent NoneType errors)
        win_labels = ['win', 'win_moonshot', 'win_trailing']
        realized = float(df[df['result'].str.lower().isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # Operational Burn Insurance
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(abs(pd.to_numeric(overhead_df['amount'], errors='coerce').sum()))
            except: 
                burn = 0.0

        tax_pot = float(df[df['result'].str.lower().isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # Tradable Balance = Vault Cash - Tax - Currently Locked Wagers
        locked_wagers = float(df[df['result'].str.upper() == 'OPEN']['wager'].sum())

        return {
            "vault_cash": vault_cash,
            "tradable_balance": float(vault_cash - tax_pot - locked_wagers),
            "tax_pot": tax_pot,
            "burn": burn,
            "trades_df": df
        }
    except Exception as e:
        print(f"CRITICAL LEDGER ERROR: {e}")
        return default_data

def calculate_unrealized(trades_df, prices_dict):
    """Calculates live floating profit with protection against None prices."""
    if trades_df is None or trades_df.empty or not isinstance(prices_dict, dict):
        return 0.0, pd.DataFrame()
        
    unreal_total = 0.0
    open_trades = trades_df[trades_df['result'].str.upper() == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = str(row.get('asset', 'UNKNOWN')).upper()
        # Look for the price in the dict regardless of case
        live_p = prices_dict.get(asset) or prices_dict.get(asset.capitalize()) or prices_dict.get('Bitcoin' if asset == 'BTC' else asset)
        
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if live_p and entry_p > 0:
            pnl = wager * ((float(live_p) - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
            
    return float(unreal_total), open_trades

def format_institutional_ledger(df, prices_dict):
    """Creates the 7-column table with crash-protection for prices_dict."""
    if df is None or df.empty: return pd.DataFrame()
    
    report = []
    now = datetime.now()
    # Safety: Ensure prices_dict is a valid dictionary to prevent crash
    safe_prices = prices_dict if isinstance(prices_dict, dict) else {}

    for _, row in df.iterrows():
        asset = str(row.get('asset', '???')).upper()
        res = str(row.get('result', 'UNKNOWN')).upper()
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if res == 'OPEN' or res == 'ACTIVE':
            status = "🟢 ACTIVE"
            # Robust lookup: Check BTC, then Btc, then Bitcoin
            live_p = safe_prices.get(asset) or safe_prices.get(asset.capitalize()) or safe_prices.get('Bitcoin' if asset == 'BTC' else '')
            mtm = float(live_p) if live_p else entry_p
            pnl = wager * ((mtm - entry_p) / entry_p) if entry_p > 0 else 0
        else:
            status = "✅ CLOSED"
            pnl = float(row.get('profit_usd', 0))
            mtm = entry_p * (1 + (pnl / wager)) if wager > 0 else entry_p
            
        ret_pct = (pnl / wager) * 100 if wager > 0 else 0
        
        try:
            ts = pd.to_datetime(row.get('timestamp'))
            delta = now - ts
            age_str = f"{delta.days}d {delta.seconds // 3600}h" if delta.days > 0 else f"{delta.seconds // 3600}h"
        except:
            age_str = "---"

        report.append({
            "Ticker": asset,
            "Status": status,
            "Age": age_str,
            "Entry Price": entry_p,
            "MTM Price": mtm,
            "Return (%)": ret_pct,
            "P/L ($)": pnl
        })
        
    return pd.DataFrame(report)
