def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Calculate target BTC exposure (position size) ∈ [0.0, 1.0] dynamically
    based on the Final Score ∈ [0.0, 1.0] and the 5-state Regime.
    """
    reg = regime.title()
    if reg == "Strong Bull":
        return 1.0
    elif reg == "Weak Bull":
        return 0.5
    elif reg in ["Neutral", "Weak Bear", "Strong Bear"]:
        return 0.0
    else:
        # Fallback to old behavior for backward compatibility if needed
        reg_upper = regime.upper()
        if reg_upper == "BEAR":
            return 0.0
        elif reg_upper == "BULL":
            return max(0.0, min(1.0, final_score))
        elif reg_upper == "SIDEWAYS":
            return max(0.0, min(0.5, final_score))
        raise ValueError(f"Unknown regime: {regime}")
