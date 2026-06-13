def calculate_target_exposure(final_score: float, regime: str) -> float:
    return max(0.0, min(1.0, final_score))
