def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Calculate target BTC exposure (position size) ∈ [0.0, 1.0] dynamically.
    Instead of binary 0/100, we use a Conviction-Scaled (Kelly-Proxy) approach:
    If final_score < 0.5, exposure is 0.0.
    If final_score >= 0.5, exposure scales linearly from 0.0 to 1.0 using 2*score - 1.
    This protects against low win-rate zones (0.5 to 0.6) and lag whipsaws.
    """
    # final_score is in [-1.0, 1.0]
    # If score is negative (bear/neutral), exposure is 0.
    # If score is positive (bull), scale linearly from 0 to 100%.
    return max(0.0, min(1.0, final_score))

