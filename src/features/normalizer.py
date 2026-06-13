import pandas as pd
import numpy as np

class RollingNormalizer:
    def __init__(self, window: int = 800):
        """
        Causal normalizer that scales unbounded metrics into [0.0, 1.0].
        Uses a rolling window to ensure no lookahead bias.
        
        Args:
            window: Number of past periods to use for min/max.
        """
        self.window = window
        
    def transform(self, series: pd.Series) -> pd.Series:
        """
        Applies causal rolling MinMax normalization.
        For time t, it only uses data from [t-window+1, t].
        Returns values bounded strictly between [0.0, 1.0].
        """
        if len(series) == 0:
            return pd.Series(dtype=float, index=series.index)
            
        rolling_min = series.rolling(window=self.window, min_periods=1).min()
        rolling_max = series.rolling(window=self.window, min_periods=1).max()
        
        range_val = rolling_max - rolling_min
        
        # Where range is 0 (all values are same), fallback to 0.5 (neutral)
        normalized = (series - rolling_min) / range_val.replace(0, np.nan)
        normalized = normalized.fillna(0.5)
        
        return normalized.clip(0.0, 1.0)
