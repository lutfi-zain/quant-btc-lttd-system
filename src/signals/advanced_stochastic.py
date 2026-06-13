import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class AdvancedStochastic(CausalFilter):
    """
    Advanced Stochastic Oscillator Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Uses dynamic lookback window scaled by ATR.
    """

    def __init__(
        self,
        dynamic_lookback=None,
        default_lookback=200,
    ):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes. If None, resolved dynamically.
            default_lookback (int): Base lookback window.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.default_lookback = default_lookback

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the Advanced Stochastic indicator score based on OHLCV data.
        Uses a vectorized multi-period For-Loop (1..129) and smooths %K with SMA 21.
        Sinyal akhir bernilai 1.0 jika rata-rata tren >= 0.0, else -1.0.

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs 'high', 'low', 'close'.

        Returns:
            pd.Series: Indicator intensities bounded in [0.0, 1.0] at the bar level.
        """
        for col in ["high", "low", "close"]:
            if col not in data.columns:
                raise ValueError(f"Input DataFrame must contain '{col}' column.")

        highs = data["high"]
        lows = data["low"]
        closes = data["close"]
        T = len(closes)

        if T == 0:
            return pd.Series(dtype=float)

        lookbacks = self._resolve_lookback(data, default_lookback=self.default_lookback)

        unique_lbs = np.unique(lookbacks)
        if len(unique_lbs) == 1:
            N = unique_lbs[0]
            max_len = int(max(129, np.ceil(129 * (N / self.default_lookback))))
            
            trends_matrix = np.zeros((max_len, T))
            for x in range(max_len):
                length = 1 + x
                ll = lows.rolling(window=length, min_periods=1).min()
                hh = highs.rolling(window=length, min_periods=1).max()
                denom = hh - ll
                stoch_raw = np.where(denom > 0, 100.0 * (closes - ll) / denom, 50.0)
                stoch_raw_series = pd.Series(stoch_raw, index=data.index)
                k = stoch_raw_series.rolling(window=21, min_periods=1).mean()
                trend = np.where(k > 50.0, 1.0, -1.0)
                trends_matrix[x] = trend
                
            start_len = int(max(1, round(1 * (N / self.default_lookback))))
            end_len = int(max(start_len, round(129 * (N / self.default_lookback))))
            
            avg = np.mean(trends_matrix[start_len - 1 : end_len, :], axis=0)
            signals = (avg + 1.0) / 2.0
        else:
            # Determine maximum length needed for the loop
            max_ratio = lookbacks.max() / self.default_lookback
            max_len = int(max(129, np.ceil(129 * max_ratio)))

            # Pre-compute trend for each length
            trends_matrix = np.zeros((max_len, T))
            for x in range(max_len):
                length = 1 + x
                ll = lows.rolling(window=length, min_periods=1).min()
                hh = highs.rolling(window=length, min_periods=1).max()
                denom = hh - ll
                stoch_raw = np.where(denom > 0, 100.0 * (closes - ll) / denom, 50.0)
                stoch_raw_series = pd.Series(stoch_raw, index=data.index)
                k = stoch_raw_series.rolling(window=21, min_periods=1).mean()
                trend = np.where(k > 50.0, 1.0, -1.0)
                trends_matrix[x] = trend

            signals = np.zeros(T)
            for t in range(T):
                ratio = lookbacks.iloc[t] / self.default_lookback
                start_len = int(max(1, round(1 * ratio)))
                end_len = int(max(start_len, round(129 * ratio)))
                signals[t] = np.mean(trends_matrix[start_len - 1 : end_len, t])

            signals = (signals + 1.0) / 2.0

        return pd.Series(signals, index=data.index, dtype=float)

