import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Aggressively finds columns and calculates Executive Summary metrics."""
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
        
        # 2. SHIELD: FORCE LOWERCASE HEADERS (Solves Asset vs asset problem)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # 3. DATA CLEANING
        df['profit_usd'] = pd.to_numeric(df['profit_usd'], errors='coerce').fillna(0)
        df['wager'] = pd.to_numeric(df['wager'], errors='coerce').fillna(0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        
        # 4. EXECUTIVE SUMMARY MATH
        win_labels = ['WIN', 'WIN_MOONSHOT', 'WIN_TRAILING']
        realized = df[df['result'].isin(win_labels + ['LOSS', 'LEGACY_CLEANUP'])]['profit_usd'].sum()
        
        # Operational Burn (if overheads exists)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                burn = abs(pd.read_csv('overheads.csv')['amount'].sum())
            except: pass

        tax_pot = df[df['result'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT
        vault_cash = INITIAL_CAPITAL + realized - burn
        
        # Tradable Balance = Vault Cash - Tax - Currently Locked Wagers
        locked_wagers = df[df['result'] == 'OPEN']['wager'].sum()

        return {
            "vault_cash": vault_cash,
            "tradable_balance": vault_cash - tax_pot - locked_wagers,
            "tax_pot": tax_pot,
            "burn": burn,
            "trades_df": df
        }
    except Exception as e:
        print(f"CRITICAL LEDGER ERROR: {e}")
        return default_data

def calculate_unrealized(trades_df, prices_dict):
    """Maps BTC to Bitcoin and calculates live floating profit."""
    if trades_df is None or trades_df.empty or not prices_dict:
        return 0.0, pd.DataFrame()
        
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    unreal_total = 0.0
    
    open_trades = trades_df[trades_df['result'] == 'OPEN'].copy()
    
    for idx, row in open_trades.iterrows():
        asset = row.get('asset', 'UNKNOWN')
        live_p = prices_dict.get(asset) or prices_dict.get(mapping.get(asset))
        entry_p = row.get('price', 0)
        wager = row.get('wager', 0)
        
        if live_p and entry_p > 0:
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
            
    return unreal_total, open_trades

def format_institutional_ledger(df, prices_dict):
    """The Transformer: Creates the 7-column high-info table we discussed."""
    if df is None or df.empty: return pd.DataFrame()
    
    mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana"}
    report = []
    now = datetime.now()

    for _, row in df.iterrows():
        asset = str(row.get('asset', '???')).upper()
        res = str(row.get('result', 'UNKNOWN')).upper()
        entry_p = row.get('price', 0)
        wager = row.get('wager', 0)
        
        # 1. LIVE MTM & RETURN MATH
        if res == 'OPEN':
            status = "🟢 ACTIVE"
            live_p = prices_dict.get(asset.capitalize()) or prices_dict.get(mapping.get(asset), 0)
            mtm = live_p
            pnl = wager * ((live_p - entry_p) / entry_p) if entry_p > 0 else 0
        else:
            status = "✅ CLOSED"
            pnl = row.get('profit_usd', 0)
            # Reverse engineer MTM for closed trades
            mtm = entry_p * (1 + (pnl / wager)) if wager > 0 else entry_p
            
        ret_pct = (pnl / wager) * 100 if wager > 0 else 0
        
        # 2. AGE CALCULATION
        try:
            ts = pd.to_datetime(row.get('timestamp'))
            delta = now - ts
            if delta.days > 0:
                age_str = f"{delta.days}d {delta.seconds // 3600}h"
            else:
                age_str = f"{delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
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
