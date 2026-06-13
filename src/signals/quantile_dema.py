import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class QuantileDEMA(CausalFilter):
    """
    Quantile Double Exponential Moving Average (QuantileDEMA) Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Computes rolling quantiles and applies the DEMA operator.
    """

    def __init__(self, dynamic_lookback=None, q_low=0.10, q_high=0.90, dema_span=200):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Dynamic window sizes. Resolved and clamped to [120, 350].
            q_low (float): Percentile for the lower band (e.g. 0.10 for 10th percentile).
            q_high (float): Percentile for the upper band (e.g. 0.90 for 90th percentile).
            dema_span (int): Exponential moving average span for DEMA calculation.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.q_low = q_low
        self.q_high = q_high
        self.dema_span = dema_span

    def _dema(self, series: pd.Series, span: int) -> pd.Series:
        """
        Calculate DEMA (Double Exponential Moving Average).
        DEMA = 2 * EMA(x) - EMA(EMA(x))
        """
        ema1 = series.ewm(span=span, adjust=False).mean()
        ema2 = ema1.ewm(span=span, adjust=False).mean()
        return 2.0 * ema1 - ema2

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the QuantileDEMA indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs to contain 'close'.

        Returns:
            pd.Series: Indicator intensities bounded in [0.0, 1.0] at the bar level.
        """
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")

        lookbacks = self._resolve_lookback(data, default_lookback=200)
        closes = data["close"].values
        T = len(closes)

        # 1. Extract rolling causal quantiles
        q_low_vals = np.full(T, np.nan)
        q_high_vals = np.full(T, np.nan)

        unique_lbs = np.unique(lookbacks)
        if len(unique_lbs) == 1:
            N = unique_lbs[0]
            if T >= N:
                q_low_series = (
                    data["close"].rolling(window=N, min_periods=N).quantile(self.q_low)
                )
                q_high_series = (
                    data["close"].rolling(window=N, min_periods=N).quantile(self.q_high)
                )
                q_low_vals = q_low_series.values
                q_high_vals = q_high_series.values
        else:
            for t in range(T):
                N = lookbacks.iloc[t]
                if t >= N - 1:
                    window_data = closes[t - N + 1 : t + 1]
                    q_low_vals[t] = np.percentile(window_data, self.q_low * 100)
                    q_high_vals[t] = np.percentile(window_data, self.q_high * 100)

        # Convert back to Series to apply DEMA operator
        q_low_series = pd.Series(q_low_vals, index=data.index)
        q_high_series = pd.Series(q_high_vals, index=data.index)

        # 2. Apply the DEMA operator to quantiles
        dema_q_low = self._dema(q_low_series.ffill(), self.dema_span)
        dema_q_high = self._dema(q_high_series.ffill(), self.dema_span)

        # 3. Threshold breakout logic to output {-1, +1}
        signals = np.ones(T)

        for t in range(T):
            # If dema bands are NaN, propagate or keep default
            if (
                pd.isna(dema_q_low.iloc[t])
                or pd.isna(dema_q_high.iloc[t])
                or pd.isna(q_low_vals[t])
            ):
                if t > 0:
                    signals[t] = signals[t - 1]
                continue

            close_val = closes[t]
            lower_band = dema_q_low.iloc[t]
            upper_band = dema_q_high.iloc[t]

            if close_val > upper_band:
                signals[t] = 1.0
            elif close_val < lower_band:
                signals[t] = -1.0
            else:
                if t > 0:
                    signals[t] = signals[t - 1]

        signals = (signals + 1.0) / 2.0
        return pd.Series(signals, index=data.index)
