from typing import Optional, Tuple

# Sizing parameters (optimized via scripts/optimize_binary.py)
EMA_SPAN = 19
SCORE_ENTRY = 0.378110
SCORE_EXIT = 0.377157
CB_ACTIVATE = -2.280818
CB_COOLOFF = -0.161039
COMP_ENTRY_BOOST = 2.866722
USE_BEAR_OVERRIDE = False

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
        if comp > CB_COOLOFF:
            cb_active = False
        else:
            return 0.0, True
    else:
        if comp <= CB_ACTIVATE:
            return 0.0, True

    # 2. Score-based entry/exit (Hysteresis)
    if prev >= 0.9:
        if final_score <= SCORE_EXIT:
            exposure = 0.0
    else:
        if final_score >= SCORE_ENTRY:
            exposure = 1.0

    # 3. BEAR regime override
    if USE_BEAR_OVERRIDE and regime == "BEAR":
        exposure = 0.0

    # 4. Composite Value Entry Boost (Deep value accumulation)
    if comp >= COMP_ENTRY_BOOST and exposure == 0.0:
        exposure = 1.0

    # 5. Strict Binary enforcement
    exposure = 1.0 if exposure > 0.5 else 0.0

    return exposure, cb_active
