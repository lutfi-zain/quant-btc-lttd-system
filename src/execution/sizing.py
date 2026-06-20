import numpy as np
import pandas as pd
from typing import Optional, Tuple

# Sizing parameters (optimized via search_metrics.py on aligned database)
SUPERSMOOTHER_PERIOD_ENTRY = 7
SUPERSMOOTHER_PERIOD_EXIT = 3
SCORE_ENTRY = 0.3057132189206123
SCORE_EXIT = 0.23605001464720393
CB_ACTIVATE = -2.260661127701853
CB_COOLOFF = 0.5006400880184867
COMP_ENTRY_BOOST = 2.000613
USE_BEAR_OVERRIDE = False
RCO_DAYS = 5
MHP_DAYS = 17
USE_MA_FILTER = True
MA_PERIOD = 226

# Ichimoku & Noise Gates parameters
ER_ENTRY = 0.25
ENTROPY_THRESH = 2.40
USE_CLOUD_GATE = True

def super_smoother(series: pd.Series, period: int) -> pd.Series:
    """
    John Ehlers' 2-pole SuperSmoother filter.
    Returns a smoothed pandas Series with the same index.
    """
    if len(series) < 2:
        return series
    
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    
    values = series.values
    out = np.zeros_like(values)
    out[0] = values[0]
    out[1] = values[1]
    
    for t in range(2, len(values)):
        out[t] = c1 * (values[t] + values[t-1]) / 2.0 + c2 * out[t-1] + c3 * out[t-2]
        
    return pd.Series(out, index=series.index)

def calculate_target_exposure(
    smoothed_score_entry: float,
    smoothed_score_exit: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
    onchain_metrics: Optional[dict] = None,
    composite_value: Optional[float] = None,
    prev_circuit_breaker_active: bool = False,
    days_since_exit: Optional[int] = None,
    days_in_position: Optional[int] = None,
    price: Optional[float] = None,
    ma_val: Optional[float] = None,
    entropy_val: Optional[float] = None,
    er_val: Optional[float] = None,
    cloud_min: Optional[float] = None
) -> Tuple[float, bool]:
    """
    Computes target exposure based on tiered state machine using asymmetric spans, RCO, and MHP.
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

    # 2. Score-based entry/exit (Hysteresis with asymmetric spans, MHP and RCO constraints)
    if prev >= 0.9:
        # Check Minimum Holding Period: default to MHP_DAYS to allow exit if not tracked
        effective_days_in_position = days_in_position if days_in_position is not None else MHP_DAYS
        if effective_days_in_position >= MHP_DAYS:
            if smoothed_score_exit <= SCORE_EXIT:
                exposure = 0.0
    else:
        # Check Re-entry cool-off: default to RCO_DAYS to allow entry if not tracked
        effective_days_since_exit = days_since_exit if days_since_exit is not None else RCO_DAYS
        if effective_days_since_exit >= RCO_DAYS:
            ma_condition = True
            if USE_MA_FILTER and price is not None and ma_val is not None:
                ma_condition = (price > ma_val)
                
            # Kaufman Efficiency Ratio Gate
            er_condition = True
            if er_val is not None:
                er_condition = (er_val >= ER_ENTRY)

            # Shannon Entropy Gate
            entropy_condition = True
            if entropy_val is not None:
                entropy_condition = (entropy_val <= ENTROPY_THRESH)

            # Ichimoku Cloud Gate
            cloud_condition = True
            if USE_CLOUD_GATE and cloud_min is not None and price is not None:
                cloud_condition = (price >= cloud_min)

            if smoothed_score_entry >= SCORE_ENTRY and ma_condition and er_condition and entropy_condition and cloud_condition:
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
