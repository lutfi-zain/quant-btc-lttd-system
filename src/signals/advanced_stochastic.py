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
        atr_short_span=14,
        atr_long_span=200,
        default_lookback=200,
        d_span=3,
        oversold_threshold=20.0,
        overbought_threshold=80.0,
    ):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes. If None, resolved dynamically using ATR.
            atr_short_span (int): Span for short-term ATR (numerator).
            atr_long_span (int): Span for long-term ATR (denominator).
            default_lookback (int): Base lookback window before volatility scaling.
            d_span (int): Span for the %D signal line EMA.
            oversold_threshold (float): Exhaustion limit for buy triggers.
            overbought_threshold (float): Exhaustion limit for sell triggers.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.atr_short_span = atr_short_span
        self.atr_long_span = atr_long_span
        self.default_lookback = default_lookback
        self.d_span = d_span
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the Advanced Stochastic indicator score based on OHLCV data.
        Uses a vectorized multi-period For-Loop (1..129) and smooths %K with SMA 21.
        Sinyal akhir bernilai 1.0 jika rata-rata tren >= 0.0, else -1.0.

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs 'high', 'low', 'close'.

        Returns:
            pd.Series: Indicator scores standardized to {-1, +1} at the bar level.
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

        # Pre-allocate trends matrix for 129 period lengths
        trends_matrix = np.zeros((129, T))

        for x in range(129):
            length = 1 + x
            ll = lows.rolling(window=length, min_periods=1).min()
            hh = highs.rolling(window=length, min_periods=1).max()
            denom = hh - ll
            stoch_raw = np.where(denom > 0, 100.0 * (closes - ll) / denom, 50.0)
            stoch_raw_series = pd.Series(stoch_raw, index=data.index)
            
            # %K smoothing (SMA 21)
            k = stoch_raw_series.rolling(window=21, min_periods=1).mean()
            trend = np.where(k > 50.0, 1.0, -1.0)
            trends_matrix[x] = trend

        avg = np.mean(trends_matrix, axis=0)
        signals = np.where(avg >= 0.0, 1.0, -1.0)

        return pd.Series(signals, index=data.index, dtype=float)

