def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Asymmetrical Sizing using ML conviction regime.
    Maximizes compounding by avoiding volatility drag.
    """
    if regime == "Strong Bull":
        return 1.5 # 1.5x Leverage
    elif regime == "Weak Bull":
        return 1.0 # 1.0x Leverage
    elif regime == "Neutral":
        return 0.0 # Stay out of neutral chop
    elif regime == "Weak Bear":
        return 0.0 # Stay out of weak bear
    elif regime == "Strong Bear":
        return 0.0 # Stay out of strong bear
        
    return 0.0
