def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Calculate target BTC exposure (position size) ∈ [0.0, 1.0] dynamically
    based on the Final Score ∈ [-1.0, +1.0] and the HMM Regime.

    BULL: Exposure scales directly with positive Final Score, up to 1.0.
    SIDEWAYS: Exposure scales with Final Score but is hard-capped at 0.5.
    BEAR: Exposure is strictly forced to 0.0.
    """
    reg = regime.upper()
    if reg == "BEAR":
        return 0.0
    elif reg == "BULL":
        return max(0.0, min(1.0, final_score))
    elif reg == "SIDEWAYS":
        return max(0.0, min(0.5, final_score))
    else:
        raise ValueError(f"Unknown regime: {regime}")
