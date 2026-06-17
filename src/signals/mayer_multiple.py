import pandas as pd
import numpy as np

def compute_mayer_multiple(close: pd.Series, window: int = 200) -> pd.Series:
    """
    Computes the Mayer Multiple: Price / SMA(window).
    Standard window for Bitcoin is 200 days.
    """
    sma = close.rolling(window=window, min_periods=1).mean()
    mayer = close / sma
    return mayer
