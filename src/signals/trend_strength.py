import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class TrendStrengthIndex(CausalFilter):
    """
    Trend Strength Index (Volatility Distance) Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Computes distance between price and Volume Weighted Moving Average (VWMA),
    normalized by Average True Range (ATR).
    """

    def __init__(
        self,
        dynamic_lookback=None,
        vwma_length=90,
        atr_length=25,
        trend_enter=1.5,
        trend_exit=1.0,
    ):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes configuration.
            vwma_length (int): Lookback period for VWMA.
            atr_length (int): Lookback period for ATR.
            trend_enter (float): Threshold to enter a bullish trend (+1).
            trend_exit (float): Threshold to enter a bearish trend (-1).
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.vwma_length = vwma_length
        self.atr_length = atr_length
        self.trend_enter = trend_enter
        self.trend_exit = trend_exit

    def _compute_vwma(
        self, close: pd.Series, volume: pd.Series, length: int
    ) -> pd.Series:
        """
        Compute Volume Weighted Moving Average (VWMA).
        """
        pv = close * volume
        sma_pv = pv.rolling(window=length, min_periods=1).mean()
        sma_v = volume.rolling(window=length, min_periods=1).mean()
        return sma_pv / sma_v.replace(0.0, np.nan)

    def _compute_atr(
        self, high: pd.Series, low: pd.Series, close: pd.Series, length: int
    ) -> pd.Series:
        """
        Compute Average True Range (ATR) using Wilder's RMA.
        """
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        tr.iloc[0] = high.iloc[0] - low.iloc[0]

        # Wilder's RMA (EMA with alpha = 1 / length)
        return tr.ewm(alpha=1.0 / length, adjust=False).mean()

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the TrendStrengthIndex indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data. Needs 'high', 'low', 'close', 'volume'.

        Returns:
            pd.Series: Indicator intensities bounded in [0.0, 1.0] at the bar level.
        """
        for col in ["high", "low", "close", "volume"]:
            if col not in data.columns:
                raise ValueError(f"Input DataFrame must contain '{col}' column.")

        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]
        T = len(close)

        # 1. Compute VWMA and ATR
        vwma = self._compute_vwma(close, volume, self.vwma_length)
        atr = self._compute_atr(high, low, close, self.atr_length)

        # 2. Compute price distance and clamp to [-2.0, 2.0]
        price_distance = (close - vwma) / atr.replace(0.0, np.nan)
        trend_strength = price_distance.clip(-2.0, 2.0).fillna(0.0)

        # 3. Convert to continuous signal in [-1.0, 1.0]
        # Divide by 2.0 to scale from [-2.0, 2.0] to [-1.0, 1.0]
        signals = trend_strength / 2.0

        return pd.Series(signals, index=data.index, dtype=float)
