def calculate_target_exposure(final_score: float, regime: str) -> float:
    """
    Asymmetrical Sizing using HMM regime and XGBoost conviction score.
    Protects against Sideways whipsaws and Bear market drawdowns.
    """
    if regime == "SIDEWAYS":
        return 0.0 # Cut completely to avoid bleeding
    elif regime == "BEAR":
        return 0.5 if final_score > 0.0 else 0.0 # Scale down, catch V-bottoms
    else: # BULL
        return 1.0 # Maximize exposure in uptrends
