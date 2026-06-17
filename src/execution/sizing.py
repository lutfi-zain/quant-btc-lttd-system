def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Asymmetrical Sizing using ML conviction regime.
    Maximizes compounding by avoiding volatility drag.
    """
    regime_upper = regime.upper() if regime else ""
    regime_map = {"BULL": "Weak Bull", "BEAR": "Weak Bear", "SIDEWAYS": "Neutral"}
    regime_mapped = regime_map.get(regime_upper, regime)
    
    if regime_mapped == "Strong Bull":
        val = 1.5 # 1.5x Leverage
    elif regime_mapped == "Weak Bull":
        val = 1.0 # 1.0x Leverage
    elif regime_mapped == "Neutral":
        val = 0.0 # Stay out of neutral chop
    elif regime_mapped == "Weak Bear":
        val = 0.0 # Stay out of weak bear
    elif regime_mapped == "Strong Bear":
        val = 0.0 # Stay out of strong bear
    else:
        val = 0.0
        
    return min(1.0, val)
