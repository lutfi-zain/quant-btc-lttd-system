import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class QuantileDEMA(CausalFilter):
    """
    Quantile Double Exponential Moving Average (QuantileDEMA) Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Computes rolling quantiles and applies the DEMA operator.
    """

    def __init__(self, dynamic_lookback=None, q_low=0.10, q_high=0.90, dema_span=None):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Dynamic window sizes. Resolved and clamped to [120, 350].
            q_low (float): Percentile for the lower band (e.g. 0.10 for 10th percentile).
            q_high (float): Percentile for the upper band (e.g. 0.90 for 90th percentile).
            dema_span (int, optional): Exponential moving average span for DEMA calculation.
                If None, dynamically scales with the resolved lookback window.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.q_low = q_low
        self.q_high = q_high
        self.dema_span = dema_span

    def _time_varying_ema(self, series: pd.Series, spans: pd.Series) -> pd.Series:
        """
        Calculate time-varying causal Exponential Moving Average.
        y_t = alpha_t * x_t + (1 - alpha_t) * y_{t-1}
        where alpha_t = 2.0 / (span_t + 1.0)
        """
        n = len(series)
        ema = np.zeros(n)

        first_valid = series.first_valid_index()
        if first_valid is None:
            return pd.Series(np.nan, index=series.index)

        start_idx = series.index.get_loc(first_valid)
        ema[:start_idx] = np.nan

        # Initialize
        x_init = series.iloc[start_idx]
        ema[start_idx] = x_init

        # Extract values for fast loop
        series_vals = series.values
        spans_vals = spans.values

        for t in range(start_idx + 1, n):
            x = series_vals[t]
            span = spans_vals[t]
            if pd.isna(x):
                ema[t] = ema[t - 1]
            else:
                alpha = 2.0 / (span + 1.0)
                ema[t] = alpha * x + (1.0 - alpha) * ema[t - 1]

        return pd.Series(ema, index=series.index)

    def _dema_dynamic(self, series: pd.Series, spans: pd.Series) -> pd.Series:
        """
        Calculate dynamic DEMA using time-varying causal EMA.
        DEMA = 2 * EMA1 - EMA2
        """
        ema1 = self._time_varying_ema(series, spans)
        ema2 = self._time_varying_ema(ema1, spans)
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

        # 2. Apply the DEMA operator to quantiles (using dynamic or constant spans)
        if self.dema_span is None:
            span_series = lookbacks
        else:
            span_series = pd.Series(self.dema_span, index=data.index)

        dema_q_low = self._dema_dynamic(q_low_series.ffill(), span_series)
        dema_q_high = self._dema_dynamic(q_high_series.ffill(), span_series)

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
