def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Calculate target BTC exposure (position size) ∈ [0.0, 1.0] dynamically
    based purely on the numeric Final Score threshold of 0.5.
    
    The `regime` argument is retained for backward compatibility with existing callers.
    """
    if final_score >= 0.5:
        return 1.0
    return 0.0
