import pandas as pd
import os
from datetime import datetime

# --- FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(prices_dict=None):
    """Calculates capital metrics with zero-value insurance and float-safety."""
    default_data = {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "burn": 0.0, "trades_df": pd.DataFrame()}
    if not os.path.exists('trades.csv'): return default_data
    try:
        df = pd.read_csv('trades.csv')
        valid_cols = [c for c in df.columns if 'Unnamed' not in str(c) and c != ""]
        df = df[valid_cols]
        df.columns = [c.lower().strip() for c in df.columns]
        
        for col in ['profit_usd', 'wager', 'price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        win_labels = ['win', 'win_moonshot', 'win_trailing']
        realized = float(df[df['result'].str.lower().isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: burn = 0.0

        tax_pot = float(df[df['result'].str.lower().isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        locked_wagers = float(df[df['result'].str.upper() == 'OPEN']['wager'].sum())

        return {
            "vault_cash": vault_cash,
            "tradable_balance": float(vault_cash - tax_pot - locked_wagers),
            "tax_pot": tax_pot, "burn": burn, "trades_df": df
        }
    except Exception as e:
        print(f"CRITICAL LEDGER ERROR: {e}")
        return default_data

def get_live_price(asset, prices_dict):
    """FORCED MATCHING with Diagnostic Feedback."""
    if not isinstance(prices_dict, dict) or not prices_dict: 
        print("⚠️ PENNY ALERT: George sent an EMPTY vault (prices_dict is None or empty)!")
        return None
    
    search_asset = str(asset).strip().upper()
    
    # 1. Show us what George actually sent
    print(f"🔍 PENNY AUDIT: Looking for '{search_asset}'. Vault Keys available: {list(prices_dict.keys())}")
    
    clean_prices = {}
    for k, v in prices_dict.items():
        if v is not None:
            try:
                # Type-Safety: ensure string numbers from George become floats
                val = float(str(v).replace(',', '').replace('$', '').strip())
                clean_prices[str(k).strip().upper()] = val
            except (ValueError, TypeError):
                print(f"❌ PENNY ERROR: Could not convert value '{v}' for key '{k}' to a number.")
                continue
    
    # 2. Check for Direct Match
    if search_asset in clean_prices:
        p = clean_prices[search_asset]
        print(f"✅ MATCH FOUND: '{search_asset}' matched directly at ${p}")
        return p
            
    # 3. Check Bridge (BTC -> BITCOIN)
    xr = {"BTC": "BITCOIN", "ETH": "ETHEREUM", "SOL": "SOLANA", "BITCOIN": "BTC"}
    target = xr.get(search_asset)
    
    if target and target in clean_prices:
        p = clean_prices[target]
        print(f"✅ BRIDGE MATCH: '{search_asset}' matched via '{target}' at ${p}")
        return p
        
    print(f"❓ NO MATCH: Could not find '{search_asset}' or bridge in vault.")
    return None

def calculate_unrealized(trades_df, prices_dict):
    if trades_df is None or trades_df.empty:
        return 0.0, pd.DataFrame()
    unreal_total = 0.0
    open_trades = trades_df[trades_df['result'].str.upper() == 'OPEN'].copy()
    for idx, row in open_trades.iterrows():
        live_p = get_live_price(row.get('asset', 'UNKNOWN'), prices_dict)
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if live_p is not None and entry_p > 0:
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
    return float(unreal_total), open_trades

def format_institutional_ledger(df, prices_dict):
    if df is None or df.empty: return pd.DataFrame()
    report = []
    now = datetime.now()
    for _, row in df.iterrows():
        asset_name = str(row.get('asset', '???'))
        res = str(row.get('result', 'UNKNOWN')).upper()
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if res == 'OPEN' or res == 'ACTIVE':
            status = "🟢 ACTIVE"
            live_p = get_live_price(asset_name, prices_dict)
            
            # This logic dictates the MTM Price update
            if live_p is not None:
                mtm = float(live_p)
            else:
                mtm = entry_p
                
            pnl = wager * ((mtm - entry_p) / entry_p) if entry_p > 0 else 0
        else:
            status = "✅ CLOSED"
            pnl = float(row.get('profit_usd', 0))
            mtm = entry_p * (1 + (pnl / wager)) if wager > 0 else entry_p
            
        ret_pct = (pnl / wager) * 100 if wager > 0 else 0
        try:
            ts = pd.to_datetime(row.get('timestamp'))
            age_str = f"{(now - ts).days}d {(now - ts).seconds // 3600}h"
        except: age_str = "---"

        report.append({
            "Ticker": asset_name.upper(), "Status": status, "Age": age_str,
            "Entry Price": entry_p, "MTM Price": mtm,
            "Return (%)": ret_pct, "P/L ($)": pnl
        })
    return pd.DataFrame(report)
