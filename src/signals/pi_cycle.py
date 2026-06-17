import pandas as pd
import numpy as np

def compute_pi_cycle_top(close: pd.Series) -> pd.Series:
    """
    Pi Cycle Top Indicator.
    Signals a market top when the 111-day SMA crosses above the 350-day SMA * 2.
    Returns the difference (distance) between the two. 
    Positive values mean the 111-day SMA has crossed above (extreme overbought).
    """
    sma_111 = close.rolling(window=111, min_periods=1).mean()
    sma_350_x2 = close.rolling(window=350, min_periods=1).mean() * 2.0
    
    # Distance: (SMA_111 / SMA_350_x2) - 1
    # When > 0, it's a Top Signal.
    distance = (sma_111 / sma_350_x2) - 1.0
    return distance

def compute_pi_cycle_bottom(close: pd.Series) -> pd.Series:
    """
    Pi Cycle Bottom Indicator.
    Signals a market bottom when the 150-day EMA crosses below the 471-day SMA.
    Returns the difference (distance) between the two.
    Negative values mean the 150-day EMA has crossed below (extreme oversold).
    """
    ema_150 = close.ewm(span=150, min_periods=1, adjust=False).mean()
    sma_471 = close.rolling(window=471, min_periods=1).mean()
    
    # Distance: (EMA_150 / SMA_471) - 1
    # When < 0, it's a Bottom Signal.
    distance = (ema_150 / sma_471) - 1.0
    return distance
