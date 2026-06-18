def apply_onchain_overrides(posteriors: dict, onchain_metrics: dict) -> dict:
    """
    Applies on-chain euphoric and cycle top overrides to HMM posterior probabilities.

    - STH-NUPL euphoric override: scales BULL probability to <= 0.50 when STH-NUPL > 0.75
    - STH-MVRV cycle top override: drives BULL probability to 0.0 when STH-MVRV > 2.0
    """
    new_posteriors = posteriors.copy()

    # 1. STH-MVRV cycle top override (STH-MVRV > 2.0)
    # This limits BULL confidence completely to drive final score <= 0
    if onchain_metrics.get("sth_mvrv", 0.0) > 2.0:
        p_bull = new_posteriors.get("BULL", 0.0)
        if p_bull > 0.0:
            new_posteriors["BULL"] = 0.0
            other_sum = new_posteriors.get("BEAR", 0.0) + new_posteriors.get(
                "SIDEWAYS", 0.0
            )
            if other_sum > 0:
                new_posteriors["BEAR"] += p_bull * (new_posteriors["BEAR"] / other_sum)
                new_posteriors["SIDEWAYS"] += p_bull * (
                    new_posteriors["SIDEWAYS"] / other_sum
                )
            else:
                new_posteriors["BEAR"] = 0.5
                new_posteriors["SIDEWAYS"] = 0.5

    # 2. STH-NUPL euphoric override (STH-NUPL > 0.75)
    # This scales BULL probability to <= 0.50
    elif onchain_metrics.get("sth_nupl", 0.0) > 0.75:
        p_bull = new_posteriors.get("BULL", 0.0)
        if p_bull > 0.50:
            diff = p_bull - 0.50
            new_posteriors["BULL"] = 0.50
            other_sum = new_posteriors.get("BEAR", 0.0) + new_posteriors.get(
                "SIDEWAYS", 0.0
            )
            if other_sum > 0:
                new_posteriors["BEAR"] += diff * (new_posteriors["BEAR"] / other_sum)
                new_posteriors["SIDEWAYS"] += diff * (
                    new_posteriors["SIDEWAYS"] / other_sum
                )
            else:
                new_posteriors["BEAR"] += diff / 2.0
                new_posteriors["SIDEWAYS"] += diff / 2.0

    return new_posteriors
