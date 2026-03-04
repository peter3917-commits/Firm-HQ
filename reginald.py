def check_safety_floor(current_balance, opening_balance, max_drawdown_pct):
    """
    Reginald calculates if we have hit the 'Safety Floor'.
    """
    drawdown_limit = opening_balance * (max_drawdown_pct / 100)
    current_loss = opening_balance - current_balance
    
    if current_loss >= drawdown_limit:
        return False, "CRITICAL: Safety Floor Breached. Trading Suspended."
    
    return True, "SAFE: Capital within risk parameters."

def get_risk_rating(yield_pct):
    if yield_pct < -2: return "High Risk"
    if yield_pct < 0: return "Caution"
    return "Stable"