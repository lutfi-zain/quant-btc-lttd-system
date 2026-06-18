from typing import Optional

def calculate_target_exposure(
    final_score: float,
    vol: float,
    regime: Optional[str] = None,
    prev_exposure: Optional[float] = None,
    onchain_metrics: Optional[dict] = None,
) -> float:
    """
    Computes target exposure to achieve > 2x B&H returns with Sharpe > 1.5.
    Hard Constraint: 0% exposure in BEAR market (no noise signals).
    """
    if regime == "BEAR":
        return 0.0
        
    # Map final_score [-1.0, 1.0] to conviction [0.0, 1.0]
    conviction = 0.5 + 0.5 * final_score
    
    if regime == "BULL":
        # Aggressive scaling during violent bull
        raw_exposure = 1.0 + (1.5 * conviction)  # Range: 1.0 to 2.5
    else:
        # SIDEWAYS: This includes steady structural bull markets (moderate drift).
        # We scale from 0.0 to 2.0x based entirely on model conviction.
        # Neutral conviction (0.5) = 1.0x (Market weight). Strong Bull (1.0) = 2.0x.
        raw_exposure = conviction * 2.0
        
    # Apply volatility dampener if vol is extreme (e.g. > 100% annualized)
    import math
    annualized_vol = vol * math.sqrt(365)
    if annualized_vol > 1.0:
        raw_exposure *= (1.0 / annualized_vol)
        
    # On-Chain Macro Top Detection (from AGENTS.md)
    if regime == "BULL" and onchain_metrics is not None:
        sth_nupl = onchain_metrics.get("sth_nupl", 0.0)
        sth_mvrv = onchain_metrics.get("sth_mvrv", 0.0)
        if sth_nupl > 0.75 or sth_mvrv > 2.0:
            # Overheated: deleverage heavily
            raw_exposure = min(raw_exposure, 0.5)
            
    # Restrict to [0.0, 2.5]
    raw_exposure = max(0.0, min(2.5, raw_exposure))
    
    if prev_exposure is None or prev_exposure == 0.0:
        return raw_exposure
        
    # Apply 5-day EMA smoothing (alpha = 2 / (5 + 1) = 1/3)
    alpha = 1.0 / 3.0
    smoothed = alpha * raw_exposure + (1.0 - alpha) * prev_exposure
    
    # Restrict daily change to max 0.3 to reduce slippage but allow quick entry/exit
    diff = smoothed - prev_exposure
    diff_clamped = max(-0.3, min(0.3, diff))
    final_exposure = prev_exposure + diff_clamped
    
    return max(0.0, min(2.5, final_exposure))
