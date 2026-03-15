import pandas as pd
import os
from datetime import datetime

# --- 🏛️ FIRM FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(conn, prices_dict=None):
    """
    Penny 3.0: Institutional Auditor.
    Hardened against Google Sheets 'Bad Data' and data type mismatches.
    """
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL, 
        "tax_pot": 0.0, 
        "burn": 0.0, 
        "trades_df": pd.DataFrame()
    }
    
    try:
        # STEP 1: Fresh Fetch
        df = conn.read(worksheet="Ledger", ttl="0")
        
        if df is None or df.empty:
            return default_data

        # STEP 2: Scannable Formatting (Lower/Strip/Safe-Float)
        df.columns = [c.lower().strip() for c in df.columns]
        for col in ['profit_usd', 'wager', 'price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        df['result_clean'] = df['result'].astype(str).str.lower().str.strip()
        win_labels = ['win', 'win_moonshot', 'win_trailing']
        
        # STEP 3: Realized P/L Calculation
        # Only sum rows that are explicitly closed
        closed_trades = df[df['result_clean'].isin(win_labels + ['loss', 'legacy_cleanup'])]
        realized = float(closed_trades['profit_usd'].sum())
        
        # STEP 4: Overhead & Burn (Local Protection)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: pass

        # STEP 5: Institutional Math
        # Tax is only owed on the PROFIT of winning trades
        tax_pot = float(df[df['result_clean'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        
        # Vault Cash = Initial + Closed P/L - Expenses
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # Locked Capital = The 'Wager' amount currently sitting in active market positions
        locked_wagers = float(df[df['result_clean'] == 'open']['wager'].sum())

        return {
            "vault_cash": round(vault_cash, 2),
            "tradable_balance": round(float(vault_cash - tax_pot - locked_wagers), 2),
            "tax_pot": round(tax_pot, 2), 
            "burn": round(burn, 2), 
            "trades_df": df
        }
    except Exception as e:
        print(f"🏛️ PENNY AUDIT ERROR: {e}")
        return default_data

def get_live_price(asset, prices_dict):
    """Institutional Price Matching with Redundancy Support."""
    if not isinstance(prices_dict, dict) or not prices_dict: 
        return None
    
    search_asset = str(asset).strip().upper()
    
    # 1. Standardize Price Inputs
    clean_prices = {}
    for k, v in prices_dict.items():
        if v is not None:
            try:
                val = float(str(v).replace(',', '').replace('$', '').strip())
                clean_prices[str(k).strip().upper()] = val
            except (ValueError, TypeError): continue
    
    # 2. Match Logic (Direct or Bridge)
    xr = {"BTC": "BITCOIN", "ETH": "ETHEREUM", "SOL": "SOLANA", "BITCOIN": "BTC", "SOLANA": "SOL", "ETHEREUM": "ETH"}
    
    if search_asset in clean_prices:
        return clean_prices[search_asset]
    
    target = xr.get(search_asset)
    if target and target in clean_prices:
        return clean_prices[target]
        
    return None

def calculate_unrealized(trades_df, prices_dict):
    """Calculates floating P/L for the Accounting Office dashboard."""
    if trades_df is None or trades_df.empty:
        return 0.0, pd.DataFrame()
    
    unreal_total = 0.0
    df_copy = trades_df.copy()
    df_copy['result_clean'] = df_copy['result'].astype(str).str.lower().str.strip()
    
    mask = df_copy['result_clean'] == 'open'
    for idx, row in df_copy[mask].iterrows():
        live_p = get_live_price(row.get('asset', 'UNKNOWN'), prices_dict)
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if live_p is not None and entry_p > 0:
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            df_copy.at[idx, 'profit_usd'] = pnl
            
    return float(unreal_total), df_copy[mask]

def format_institutional_ledger(df, prices_dict):
    """Generates the clean 'Executive Summary' table for Tab 2."""
    if df is None or df.empty: return pd.DataFrame()
    report = []
    now = datetime.now().replace(tzinfo=None)
    
    df_working = df.copy()
    df_working['result_clean'] = df_working['result'].astype(str).str.lower().str.strip()
    
    for _, row in df_working.iterrows():
        asset_name = str(row.get('asset', '???')).strip().upper()
        res_clean = row.get('result_clean', 'unknown')
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if res_clean == 'open':
            status = "🟢 ACTIVE"
            live_p = get_live_price(asset_name, prices_dict)
            mtm = float(live_p) if live_p is not None else entry_p
            pnl = wager * ((mtm - entry_p) / entry_p) if entry_p > 0 else 0
        else:
            status = "✅ CLOSED"
            pnl = float(row.get('profit_usd', 0))
            mtm = entry_p * (1 + (pnl / wager)) if (wager > 0 and entry_p > 0) else entry_p
            
        ret_pct = (pnl / wager) * 100 if wager > 0 else 0
        
        try:
            ts = pd.to_datetime(row.get('timestamp')).tz_localize(None)
            diff = now - ts
            age_str = f"{diff.days}d {diff.seconds // 3600}h"
        except: age_str = "---"

        report.append({
            "Ticker": asset_name, 
            "Status": status, 
            "Age": age_str,
            "Entry Price": round(entry_p, 2), 
            "MTM Price": round(mtm, 2),
            "Return (%)": round(ret_pct, 2), 
            "P/L ($)": round(pnl, 2)
        })
    return pd.DataFrame(report)
