import numpy as np
import pandas as pd
from src.signals.base import CausalFilter


class KalmanRSI(CausalFilter):
    """
    Kalman Filtered Relative Strength Index (RSI) Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Applies a 1D Kalman filter to the price series to estimate a smoothed
    hidden price state, then computes RSI on this state.
    Standardizes output to a continuous intensity in [0.0, 1.0].
    """

    def __init__(
        self,
        dynamic_lookback=None,
        rsi_period=50,
        process_noise=0.75,
        measurement_noise=205.0,
        smooth=False,
        smooth_period=7,
        smooth_type="Ema",
    ):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes for the filter.
            rsi_period (int): Lookback period for standard RSI calculation.
            process_noise (float): Process noise covariance (Q) for Kalman filter.
            measurement_noise (float): Measurement noise covariance (R) for Kalman filter.
            smooth (bool): Whether to smooth the RSI using a moving average.
            smooth_period (int): Lookback period for smoothing.
            smooth_type (str): Type of smoothing MA ('Ema', 'Sma', etc.).
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.rsi_period = rsi_period
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.smooth = smooth
        self.smooth_period = smooth_period
        self.smooth_type = smooth_type

    def _apply_kalman(self, price: pd.Series) -> pd.Series:
        """
        Apply a 1D Kalman Filter to the input price series.
        """
        n = len(price)
        filtered = np.zeros(n)

        # Find the first non-NaN price index
        first_valid = price.first_valid_index()
        if first_valid is None:
            return pd.Series(np.nan, index=price.index)

        start_idx = price.index.get_loc(first_valid)
        filtered[:start_idx] = np.nan

        # Initialization
        x = price.iloc[start_idx]
        p = 1.0  # Initial error covariance
        filtered[start_idx] = x

        for t in range(start_idx + 1, n):
            val = price.iloc[t]
            if pd.isna(val):
                filtered[t] = x
                continue

            # 1. Prediction Step
            x_pred = x
            p_pred = p + self.process_noise

            # 2. Kalman Gain
            k_gain = p_pred / (p_pred + self.measurement_noise)

            # 3. Update Step
            x = x_pred + k_gain * (val - x_pred)
            p = (1.0 - k_gain) * p_pred

            filtered[t] = x

        return pd.Series(filtered, index=price.index)

    def _pandas_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate standard Wilder's RSI using pandas ewm.
        """
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)

        # Wilder's EMA (RMA) uses alpha = 1 / period
        roll_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
        roll_down = down.ewm(alpha=1.0 / period, adjust=False).mean()

        rs = roll_up / roll_down.replace(0.0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.fillna(50.0)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the RSI-50 indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data.

        Returns:
            pd.Series: Indicator intensities bounded in [-1.0, 1.0] at the bar level.
        """
        # Resolve price source
        if all(col in data.columns for col in ["open", "high", "low", "close"]):
            pricesource = (
                data["open"] + data["high"] + data["low"] + data["close"]
            ) / 4.0
        elif "close" in data.columns:
            pricesource = data["close"]
        else:
            raise ValueError("Input DataFrame must contain 'close' column.")

        # Compute RSI directly on pricesource (no Kalman filter)
        rsi = self._pandas_rsi(pricesource, self.rsi_period)

        # Convert to binary signal: +1 if RSI > 50, else -1
        score = pd.Series(np.where(rsi > 50.0, 1.0, -1.0), index=pricesource.index)
        score[pricesource.isna()] = np.nan
        
        return score
