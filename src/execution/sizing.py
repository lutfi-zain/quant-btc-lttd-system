from typing import Optional

def calculate_target_exposure(
    final_score: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
) -> float:
    """
    Computes target exposure based on the absolute value of final_score (conviction)
    and realized volatility.
    
    Formula:
      base_exposure = 0.5 + 0.5 * |final_score|
      vol_scalar = max(0.3, 1.0 - vol / 0.8)
      target_exposure = base_exposure * vol_scalar
      
    Bounded between [0.3, 1.0].
    Smoothed using a 5-day EMA with a maximum daily change limit of 0.2.
    """
    conviction = abs(final_score)
    base_exposure = 0.5 + 0.5 * conviction
    vol_scalar = max(0.3, 1.0 - vol / 0.8)
    
    raw_exposure = base_exposure * vol_scalar
    raw_exposure = max(0.3, min(1.0, raw_exposure))
    
    if prev_exposure is None or prev_exposure == 0.0:
        return raw_exposure
        
    # Apply 5-day EMA smoothing (alpha = 2 / (5 + 1) = 1/3)
    alpha = 1.0 / 3.0
    smoothed = alpha * raw_exposure + (1.0 - alpha) * prev_exposure
    
    # Restrict daily change to max 0.2
    diff = smoothed - prev_exposure
    diff_clamped = max(-0.2, min(0.2, diff))
    final_exposure = prev_exposure + diff_clamped
    
    return max(0.3, min(1.0, final_exposure))
