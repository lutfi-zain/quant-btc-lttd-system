from typing import Optional, Tuple

def calculate_target_exposure(
    final_score: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
    onchain_metrics: Optional[dict] = None,
    composite_value: Optional[float] = None,
    prev_circuit_breaker_active: bool = False
) -> Tuple[float, bool]:
    """
    Computes target exposure based on tiered state machine.
    Returns (target_exposure, is_circuit_breaker_active).
    """
    prev = prev_exposure if prev_exposure is not None else 0.0
    exposure = prev
    cb_active = prev_circuit_breaker_active

    comp = composite_value if composite_value is not None else 0.0

    # 1. Valuation Circuit Breaker with Cool-off
    if cb_active:
        if comp > 0.803830:
            cb_active = False
        else:
            return 0.0, True
    else:
        if comp <= -2.032903:
            return 0.0, True

    # 2. Score-based entry/exit (Hysteresis)
    if prev >= 0.9:
        if final_score <= 0.386242:
            exposure = 0.0
    else:
        if final_score >= 0.470671:
            exposure = 1.0

    # 3. Composite Value Entry Boost (Deep value accumulation)
    if comp >= 2.000613 and exposure == 0.0:
        exposure = 1.0

    # 4. Strict Binary enforcement
    exposure = 1.0 if exposure > 0.5 else 0.0

    return exposure, cb_active
