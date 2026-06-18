from typing import Optional

def calculate_target_exposure(
    final_score: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
    onchain_metrics: Optional[dict] = None,
) -> float:
    """
    Computes target exposure based on tiered state machine.
    """
    if regime == "BEAR":
        return 0.0

    prev = prev_exposure if prev_exposure is not None else 0.0
    raw_exposure = prev

    if prev >= 0.9:
        if final_score <= 0.11:
            raw_exposure = 0.0
    else:
        if final_score >= 0.65:
            raw_exposure = 1.0

    if onchain_metrics is not None and raw_exposure > 0:
        sth_nupl = onchain_metrics.get("sth_nupl", 0.0)
        sth_mvrv = onchain_metrics.get("sth_mvrv", 0.0)
        
        if sth_nupl > 0.75 or sth_mvrv > 2.0:
            raw_exposure = 0.0

    return raw_exposure
