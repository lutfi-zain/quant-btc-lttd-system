import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class IchimokuCausalFilter(CausalFilter):
    """
    Causal Ichimoku Kinko Hyo Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Provides various boolean edges and combined signals (e.g. Price > Senkou B and Price > Causal Chikou).
    """

    def __init__(
        self,
        dynamic_lookback=None,
        tenkan_length=9,
        kijun_length=26,
        senkou_b_length=52,
        displacement=26,
        rule="P_gt_SB_AND_P_gt_C"
    ):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes. If None, resolved dynamically.
            tenkan_length (int): Period for Tenkan-sen (default 9).
            kijun_length (int): Period for Kijun-sen (default 26).
            senkou_b_length (int): Period for Senkou Span B (default 52).
            displacement (int): Displacement period for Spans and Chikou (default 26).
            rule (str): The rule combination to compute:
                - "P_gt_SB_AND_P_gt_C": Price > Senkou B AND Price > Causal Chikou (Top 1)
                - "P_gt_T_AND_P_gt_SA": Price > Tenkan AND Price > Senkou A (Top 2)
                - "P_gt_T_AND_T_gt_K": Price > Tenkan AND Tenkan > Kijun (Top 3)
                - "P_gt_C": Price > Causal Chikou (Top 7)
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.tenkan_length = tenkan_length
        self.kijun_length = kijun_length
        self.senkou_b_length = senkou_b_length
        self.displacement = displacement
        self.rule = rule

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the causal Ichimoku indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): Needs 'high', 'low', 'close'.

        Returns:
            pd.Series: Indicator intensities in [-1.0, 1.0] at the bar level.
        """
        for col in ["high", "low", "close"]:
            if col not in data.columns:
                raise ValueError(f"Input DataFrame must contain '{col}' column.")

        high = data["high"]
        low = data["low"]
        close = data["close"]
        T = len(close)

        if T == 0:
            return pd.Series(dtype=float)

        # 1. Tenkan-sen (9-period midpoint)
        tenkan = (high.rolling(self.tenkan_length).max() + low.rolling(self.tenkan_length).min()) / 2

        # 2. Kijun-sen (26-period midpoint)
        kijun = (high.rolling(self.kijun_length).max() + low.rolling(self.kijun_length).min()) / 2

        # 3. Senkou Span A (shifted forward 26 periods)
        # Causally, at bar t, we evaluate the span that was calculated at t - displacement
        sa = ((tenkan + kijun) / 2).shift(self.displacement)

        # 4. Senkou Span B (52-period midpoint shifted forward 26 periods)
        sb = ((high.rolling(self.senkou_b_length).max() + low.rolling(self.senkou_b_length).min()) / 2).shift(self.displacement)

        # 5. Chikou Causal (close from 26 periods ago)
        chikou = close.shift(self.displacement)

        # Apply the selected rule
        if self.rule == "P_gt_SB_AND_P_gt_C":
            # Price > Senkou B AND Price > Causal Chikou
            bullish = (close > sb) & (close > chikou)
        elif self.rule == "P_gt_T_AND_P_gt_SA":
            # Price > Tenkan AND Price > Senkou A
            bullish = (close > tenkan) & (close > sa)
        elif self.rule == "P_gt_T_AND_T_gt_K":
            # Price > Tenkan AND Tenkan > Kijun
            bullish = (close > tenkan) & (tenkan > kijun)
        elif self.rule == "P_gt_C":
            # Price > Causal Chikou
            bullish = close > chikou
        else:
            raise ValueError(f"Unknown Ichimoku rule: {self.rule}")

        # Return continuous-like signal: 1.0 for bullish, -1.0 for bearish (filled with 0.0 for NaNs at start)
        signals = np.where(bullish, 1.0, -1.0)
        
        # Handle initial warmups/NaNs cleanly
        nan_mask = sb.isna() | chikou.isna()
        signals[nan_mask] = 0.0

        return pd.Series(signals, index=data.index, dtype=float)
