from typing import Optional

def calculate_target_exposure(
    final_score: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
    posteriors: Optional[dict] = None,
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
    import math
    
    # Convert daily standard deviation to annualized volatility
    annualized_vol = vol * math.sqrt(365)
    
    # Target 60% annualized volatility for the portfolio
    target_vol = 0.60
    safe_vol = max(0.20, annualized_vol)
    vol_target_exposure = target_vol / safe_vol
    
    # Map final_score [-1.0, 1.0] to conviction [0.0, 1.0]
    conviction = 0.5 + 0.5 * final_score
    
    if regime == "BEAR":
        raw_exposure = 0.0
    else:
        raw_exposure = vol_target_exposure * conviction
        # Allow up to 2.0x leverage during low-volatility bull markets
        raw_exposure = max(0.0, min(2.0, raw_exposure))
    
    if prev_exposure is None or prev_exposure == 0.0:
        return raw_exposure
        
    # Apply 5-day EMA smoothing (alpha = 2 / (5 + 1) = 1/3)
    alpha = 1.0 / 3.0
    smoothed = alpha * raw_exposure + (1.0 - alpha) * prev_exposure
    
    # Restrict daily change to max 0.2
    diff = smoothed - prev_exposure
    diff_clamped = max(-0.2, min(0.2, diff))
    final_exposure = prev_exposure + diff_clamped
    
    # On-Chain Macro Top Detection (from AGENTS.md)
    # If the market is completely overheated, we must defensively cap our max exposure
    # to avoid the massive 45% lag drawdown before the HMM detects a bear regime.
    nupl = posteriors.get("sth_nupl", 0.0) if posteriors else 0.0
    sth_mvrv = posteriors.get("sth_mvrv", 0.0) if posteriors else 0.0
    
    # Max normal exposure is 2.0 (2x leverage)
    cap = 2.0
    if nupl > 0.75 or sth_mvrv > 2.0:
        cap = 0.3  # Drastically cut exposure at the peak of a bubble
    elif nupl > 0.65 or sth_mvrv > 1.5:
        cap = 0.5  # Start scaling out as it gets frothy
    
    final_exposure = min(final_exposure, cap)
    
    if regime == "BEAR":
        return max(0.0, min(2.0, final_exposure))
    return max(0.0, min(2.0, final_exposure))
