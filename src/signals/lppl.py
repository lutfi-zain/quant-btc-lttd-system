import numpy as np
import pandas as pd
from src.signals.base import CausalFilter
from src.features.normalizer import RollingNormalizer

class LPPLOscillator(CausalFilter):
    """
    Log-Periodic Power Law (LPPL) Proxy Oscillator.
    Subclasses CausalFilter to enforce strict causality.
    
    Instead of full non-linear optimization (which is too slow for rolling windows),
    this uses a rolling quadratic fit on the log-price to detect super-exponential 
    growth (a hallmark of bubbles). A positive quadratic coefficient indicates 
    accelerating log-growth (bubble regime), while negative indicates deceleration.
    """

    def __init__(self, dynamic_lookback=None, default_window=90):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes for the fit.
            default_window (int): Default window for rolling fit if dynamic is not provided.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.default_window = default_window

    def compute(self, data: pd.DataFrame) -> pd.Series:
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")
            
        log_price = np.log(data["close"])
        lookbacks = self._resolve_lookback(data, default_lookback=self.default_window)
        max_lookback = int(lookbacks.max()) if len(lookbacks) > 0 else self.default_window
        
        # We can optimize rolling quadratic fit using convolution or pandas rolling apply
        # Since rolling apply might be slow, let's use a vectorized approach for a fixed window
        # (Assuming max_lookback is roughly the window we want to use, or we just use default_window for speed)
        
        w = self.default_window
        # t is 0, 1, 2, ..., w-1
        t = np.arange(w)
        t_mean = np.mean(t)
        t2 = t**2
        
        # We want to solve for beta_2 in y = beta_0 + beta_1 t + beta_2 t^2
        # We can construct the design matrix X and find (X^T X)^-1 X^T
        X = np.column_stack((np.ones(w), t, t2))
        inv_XT_X = np.linalg.inv(X.T @ X)
        proj_matrix = inv_XT_X @ X.T
        # proj_matrix[2, :] gives the weights to multiply with y to get beta_2
        beta2_weights = proj_matrix[2, :]
        
        # Apply convolution to get rolling beta_2
        # np.convolve reverses the weights, which is what we want for a rolling dot product of past w prices
        beta2 = np.convolve(log_price.values, beta2_weights[::-1], mode='full')[:len(log_price)]
        beta2_series = pd.Series(beta2, index=log_price.index)
        beta2_series.iloc[:w-1] = np.nan
        
        # Normalize to [0, 1]
        normalizer = RollingNormalizer(window=max_lookback)
        score = normalizer.transform(beta2_series)
        
        return score
