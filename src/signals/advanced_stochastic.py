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

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs 'high', 'low', 'close'.

        Returns:
            pd.Series: Indicator scores standardized to {-1, +1} at the bar level.
        """
        for col in ["high", "low", "close"]:
            if col not in data.columns:
                raise ValueError(f"Input DataFrame must contain '{col}' column.")

        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values
        T = len(closes)

        # 1. Resolve dynamic lookback using ATR scaling if dynamic_lookback not explicitly provided
        if self.dynamic_lookback is None:
            # Compute True Range (TR)
            prev_close = data["close"].shift(1)
            tr1 = data["high"] - data["low"]
            tr2 = (data["high"] - prev_close).abs()
            tr3 = (data["low"] - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR calculations
            atr_short = tr.ewm(span=self.atr_short_span, adjust=False).mean()
            atr_long = tr.ewm(span=self.atr_long_span, adjust=False).mean()

            # Volatility ratio: short ATR / long ATR
            vol_ratio = atr_short / (atr_long + 1e-8)

            # Scale lookback: inverse of volatility ratio
            raw_lookback = self.default_lookback / (vol_ratio + 1e-8)
            lookbacks = self._resolve_lookback(
                data, default_lookback=self.default_lookback
            )
            # Override with ATR-scaled lookback (which gets re-resolved and clamped)
            self.dynamic_lookback = raw_lookback
            lookbacks = self._resolve_lookback(
                data, default_lookback=self.default_lookback
            )
            # Reset dynamic_lookback to None so next calls recalculate
            self.dynamic_lookback = None
        else:
            lookbacks = self._resolve_lookback(
                data, default_lookback=self.default_lookback
            )

        # 2. Compute %K values
        k_vals = np.full(T, np.nan)
        for t in range(T):
            N = lookbacks.iloc[t]
            start_idx = max(0, t - N + 1)
            hh = np.max(highs[start_idx : t + 1])
            ll = np.min(lows[start_idx : t + 1])
            denom = hh - ll
            if denom > 0:
                k_vals[t] = 100.0 * (closes[t] - ll) / denom
            else:
                k_vals[t] = 50.0  # neutral midpoint

        # 3. Compute %D line (causal EMA of %K)
        k_series = pd.Series(k_vals, index=data.index).ffill().fillna(50.0)
        d_series = k_series.ewm(span=self.d_span, adjust=False).mean()

        # 4. Generate crossover signals in exhaustion zones
        signals = np.ones(T)

        for t in range(T):
            if t == 0:
                continue

            k_val = k_series.iloc[t]
            d_val = d_series.iloc[t]
            k_prev = k_series.iloc[t - 1]
            d_prev = d_series.iloc[t - 1]

            # Standard default state propagation
            signals[t] = signals[t - 1]

            # Bullish crossover reversal (oversold)
            if k_prev < d_prev and k_val >= d_val:
                if (
                    k_val < self.oversold_threshold
                    or d_val < self.oversold_threshold
                    or k_prev < self.oversold_threshold
                    or d_prev < self.oversold_threshold
                ):
                    signals[t] = 1.0

            # Bearish crossover reversal (overbought)
            elif k_prev > d_prev and k_val <= d_val:
                if (
                    k_val > self.overbought_threshold
                    or d_val > self.overbought_threshold
                    or k_prev > self.overbought_threshold
                    or d_prev > self.overbought_threshold
                ):
                    signals[t] = -1.0

        return pd.Series(signals, index=data.index)
