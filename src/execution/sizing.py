def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Calculate target BTC exposure (position size) ∈ [0.0, 1.0] dynamically.
    Instead of binary 0/100, we use a Conviction-Scaled (Kelly-Proxy) approach:
    # final_score is natively in [-1.0, 1.0] domain.
    # If score is negative (bear/neutral), exposure is 0.
    # If score is positive (bull), scale linearly from 0 to 100%.
    """
    return max(0.0, min(1.0, final_score))
