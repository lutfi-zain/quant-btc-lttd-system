import pandas as pd
from src.signals.base import CausalFilter


class KaufmanEfficiencyRatioFilter(CausalFilter):
    """
    Kaufman Efficiency Ratio (ER) (Fractal Family).
    Measures the net price displacement relative to the sum of absolute changes.
    """

    def __init__(self, dynamic_lookback=None, window: int = 14):
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.window = window

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the Kaufman Efficiency Ratio.
        """
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")

        close = data["close"]
        change = close.diff().abs()
        volatility = change.rolling(self.window).sum()
        direction = close.diff(self.window).abs()
        
        er = direction / volatility
        return er.fillna(0.0)
