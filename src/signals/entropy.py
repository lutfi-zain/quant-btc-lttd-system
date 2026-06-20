import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class ShannonEntropyFilter(CausalFilter):
    """
    Shannon Entropy of rolling returns (Entropy & Information family).
    Measures the randomness/complexity of the price return distribution.
    """

    def __init__(self, dynamic_lookback=None, window: int = 15, bins: int = 6):
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.window = window
        self.bins = bins

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the rolling Shannon Entropy of close price returns.
        """
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")

        close = data["close"]
        returns = close.pct_change().fillna(0.0)

        def calc_shannon(x):
            if len(x) < self.window:
                return np.nan
            counts, _ = np.histogram(x, bins=self.bins)
            probs = counts / len(x)
            probs = probs[probs > 0]
            return -np.sum(probs * np.log2(probs))

        return returns.rolling(window=self.window).apply(calc_shannon, raw=True)
