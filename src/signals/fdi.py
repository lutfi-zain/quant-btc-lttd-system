import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class FDI(CausalFilter):
    """
    Fractal Dimension Index (FDI) Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Uses Sevcik's algorithm over a rolling window.
    """

    def __init__(self, dynamic_lookback=None, ema_span=200, reversion_multiplier=1.0):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Dynamic window sizes. Resolved and clamped to [120, 350].
            ema_span (int): Span for the causal baseline EMA.
            reversion_multiplier (float): Multiplier for standard deviation bands.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.ema_span = ema_span
        self.reversion_multiplier = reversion_multiplier

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the FDI indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs to contain 'close'.

        Returns:
            pd.Series: Indicator scores standardized to {-1, +1} at the bar level.
        """
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")

        lookbacks = self._resolve_lookback(data, default_lookback=200)
        closes = data["close"].values
        T = len(closes)

        # 1. Compute rolling Fractal Dimension (D) using Sevcik's algorithm
        D = np.full(T, np.nan)

        # Check if lookbacks are uniform to use vectorized calculation
        unique_lbs = np.unique(lookbacks)
        if len(unique_lbs) == 1:
            N = unique_lbs[0]
            if T >= N:
                shape = (T - N + 1, N)
                strides = (closes.strides[0], closes.strides[0])
                windows = np.lib.stride_tricks.as_strided(
                    closes, shape=shape, strides=strides
                )

                y_min = np.min(windows, axis=1, keepdims=True)
                y_max = np.max(windows, axis=1, keepdims=True)
                denom = y_max - y_min
                denom_fixed = np.where(denom == 0, 1.0, denom)

                norm_windows = (windows - y_min) / denom_fixed
                dy = np.diff(norm_windows, axis=1)
                dx_sq = (1.0 / (N - 1)) ** 2
                L = np.sum(np.sqrt(dx_sq + dy**2), axis=1)

                D_vals = 1.0 + np.log(L) / np.log(2 * (N - 1))
                D_vals = np.where(denom.flatten() == 0, 1.0, D_vals)
                D[N - 1 :] = D_vals
        else:
            # Fall back to step-by-step rolling calculation if window is dynamic
            for t in range(T):
                N = lookbacks.iloc[t]
                if t >= N - 1:
                    y = closes[t - N + 1 : t + 1]
                    y_min = np.min(y)
                    y_max = np.max(y)
                    if y_max == y_min:
                        D[t] = 1.0
                    else:
                        norm_y = (y - y_min) / (y_max - y_min)
                        dy = np.diff(norm_y)
                        dx_sq = (1.0 / (N - 1)) ** 2
                        L = np.sum(np.sqrt(dx_sq + dy**2))
                        D[t] = 1.0 + np.log(L) / np.log(2 * (N - 1))

        # 2. Compute EMA and rolling standard deviation for the baseline
        ema = data["close"].ewm(span=self.ema_span, adjust=False).mean()
        std = data["close"].rolling(window=self.ema_span, min_periods=1).std().fillna(0)

        # 3. Calculate the discrete {-1, +1} signals using hysteresis
        signals = np.ones(T)
        is_trending = True

        for t in range(T):
            dt = D[t]
            if pd.isna(dt):
                if t > 0:
                    signals[t] = signals[t - 1]
                continue

            # Hysteresis band: 1.45 to 1.55
            if dt < 1.45:
                is_trending = True
            elif dt > 1.55:
                is_trending = False

            close_val = closes[t]
            ema_val = ema.iloc[t]
            std_val = std.iloc[t]

            if is_trending:
                # Trend-following behavior
                if close_val >= ema_val:
                    signals[t] = 1.0
                else:
                    signals[t] = -1.0
            else:
                # Mean-reverting behavior
                upper = ema_val + self.reversion_multiplier * std_val
                lower = ema_val - self.reversion_multiplier * std_val
                if close_val > upper:
                    signals[t] = -1.0
                elif close_val < lower:
                    signals[t] = 1.0
                else:
                    if t > 0:
                        signals[t] = signals[t - 1]
                    else:
                        signals[t] = 1.0

        return pd.Series(signals, index=data.index)
