import numpy as np
import pandas as pd
import scipy.fft
from src.signals.base import CausalFilter


class AdaptiveFourierSupertrend(CausalFilter):
    """
    Adaptive Fourier Transform Supertrend (Indicator 5).
    Operates in the frequency domain, dynamically tuning the ATR period
    to the dominant market cycle frequency (T_dom).
    Standardizes output to a continuous intensity in [0.0, 1.0].
    """

    def __init__(
        self, fft_window=256, min_period=10, multiplier=3.0, dynamic_lookback=None
    ):
        """
        Args:
            fft_window (int): Default FFT lookback window size.
            min_period (int): Minimum ATR period allowed (clamping lower bound).
            multiplier (float): Supertrend volatility band multiplier.
            dynamic_lookback: Lookback window size configuration (passed to CausalFilter).
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.fft_window = fft_window
        self.min_period = min_period
        self.multiplier = multiplier

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the Adaptive Fourier Supertrend score.

        Args:
            data (pd.DataFrame): OHLCV data.

        Returns:
            pd.Series: Indicator intensities bounded in [0.0, 1.0] at the bar level.
        """
        # Normalize column names to lowercase
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]

        # Resolve lookback window sizes
        lookbacks = self._resolve_lookback(df, default_lookback=self.fft_window)

        # 1. Noise mitigation: apply 5-day EMA on raw close prices
        smoothed_close = df["close"].ewm(span=5, adjust=False).mean()

        # Calculate log returns of smoothed close prices
        log_returns = np.log(smoothed_close).diff().fillna(0)

        # 2. Extract dominant spectral period (T_dom) via sliding window FFT
        t_dom_raw = []
        for t in range(len(df)):
            lb = lookbacks.iloc[t]
            # Strictly causal window up to t-1
            w = log_returns.iloc[max(0, t - lb) : t]
            L = len(w)

            # Edge case handling: first few bars before stabilization
            if L < 30:
                t_dom_raw.append(float(lb))
            else:
                coeffs = scipy.fft.rfft(w.values)
                magnitudes = np.abs(coeffs)
                if len(magnitudes) > 1:
                    # Ignore DC component at index 0
                    k_star = np.argmax(magnitudes[1:]) + 1
                    t_dom_raw.append(L / k_star)
                else:
                    t_dom_raw.append(float(lb))

        t_dom_raw = pd.Series(t_dom_raw, index=df.index)

        # Noise mitigation on T_dom: rolling 5-day median
        t_dom = t_dom_raw.rolling(window=5, min_periods=1).median()

        # 3. Dynamic ATR period scaling
        atr_period = (t_dom / 2).apply(np.floor).astype(int).clip(lower=self.min_period)

        # Calculate True Range (TR)
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        tr.iloc[0] = high.iloc[0] - low.iloc[0]

        # Compute dynamic ATR (mean of TR over the dynamic lookback window)
        atr_values = np.zeros(len(df))
        tr_vals = tr.values
        atr_periods = atr_period.values
        for t in range(len(df)):
            p = atr_periods[t]
            start_idx = max(0, t - p + 1)
            atr_values[t] = np.mean(tr_vals[start_idx : t + 1])
        atr = pd.Series(atr_values, index=df.index)

        # 4. Supertrend band logic
        midpoint = (high + low) / 2.0
        basic_upper = midpoint + self.multiplier * atr
        basic_lower = midpoint - self.multiplier * atr

        upper_band = np.zeros(len(df))
        lower_band = np.zeros(len(df))
        trend = np.ones(len(df), dtype=float)

        # Initialize first bar
        upper_band[0] = basic_upper.iloc[0]
        lower_band[0] = basic_lower.iloc[0]
        trend[0] = 1.0 if close.iloc[0] >= midpoint.iloc[0] else -1.0

        close_vals = close.values
        bu_vals = basic_upper.values
        bl_vals = basic_lower.values

        for t in range(1, len(df)):
            # Recalculate bands recursively
            if bl_vals[t] > lower_band[t - 1] or close_vals[t - 1] < lower_band[t - 1]:
                lower_band[t] = bl_vals[t]
            else:
                lower_band[t] = lower_band[t - 1]

            if bu_vals[t] < upper_band[t - 1] or close_vals[t - 1] > upper_band[t - 1]:
                upper_band[t] = bu_vals[t]
            else:
                upper_band[t] = upper_band[t - 1]

            # Determine Trend Direction
            if trend[t - 1] == 1.0:
                if close_vals[t] < lower_band[t]:
                    trend[t] = -1.0
                else:
                    trend[t] = 1.0
            else:
                if close_vals[t] > upper_band[t]:
                    trend[t] = 1.0
                else:
                    trend[t] = -1.0
        
        # Convert binary trend into a continuous intensity [0.0, 1.0]
        # Calculate where the close price sits between the lower and upper bands
        band_width = upper_band - lower_band
        # Avoid division by zero
        band_width = np.where(band_width <= 0, 1e-8, band_width)
        
        # Raw positional intensity
        raw_intensity = (close_vals - lower_band) / band_width
        
        # Clip strictly to [0.0, 1.0]
        intensity_clipped = np.clip(raw_intensity, 0.0, 1.0)
        
        # Smooth the intensity to prevent erratic jumps using a 5-day EMA
        trend_intensity = pd.Series(intensity_clipped, index=data.index).ewm(span=5, adjust=False).mean()

        return trend_intensity
