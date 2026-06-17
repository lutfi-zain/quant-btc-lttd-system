import numpy as np
import pandas as pd
from src.signals.base import CausalFilter
from src.features.normalizer import RollingNormalizer

class FractionalDifferentiation(CausalFilter):
    """
    Fractional Differentiation Technical Indicator.
    Subclasses CausalFilter to enforce strict causality.
    Applies fractional differencing to the log price series to achieve
    stationarity while retaining memory (unlike standard integer differencing).
    """

    def __init__(self, dynamic_lookback=None, d=0.5, tau=1e-4):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Window sizes for the normalizer.
            d (float): Fractional differentiation order.
            tau (float): Threshold for weight truncation.
        """
        super().__init__(dynamic_lookback=dynamic_lookback)
        self.d = d
        self.tau = tau

    def _get_weights(self):
        """
        Calculates weights for fractional differencing until weight drops below tau.
        """
        w = [1.0]
        k = 1
        while True:
            w_next = -w[-1] / k * (self.d - k + 1)
            if abs(w_next) < self.tau:
                break
            w.append(w_next)
            k += 1
        return np.array(w[::-1]) # reverse so that w[-1] is the weight for the current observation

    def compute(self, data: pd.DataFrame) -> pd.Series:
        if "close" not in data.columns:
            raise ValueError("Input DataFrame must contain 'close' column.")
            
        log_price = np.log(data["close"])
        w = self._get_weights()
        w_len = len(w)
        
        # Apply weights
        # frac_diff at time t is sum_{k=0}^{w_len-1} w[k] * log_price[t - (w_len - 1 - k)]
        # We can use np.convolve with 'valid' mode
        
        # To avoid Lookahead, we convolve past prices with w. 
        # w is already reversed. So np.convolve(log_price, w, mode='valid')
        # Wait, if w is [w_{k-1}, ..., w_0], then convolve(price, w) gives sum w_i p_{t-i}.
        # Let's write it carefully.
        
        # Let standard w_k be the weight for L^k.
        # w_0 = 1, w_1 = -d, w_2 = d(d-1)/2, etc.
        # we have a sequence of prices: p_{t-k}, ..., p_t
        # we want w_0 * p_t + w_1 * p_{t-1} + ... + w_k * p_{t-k}
        
        w_standard = [1.0]
        k = 1
        while True:
            w_next = -w_standard[-1] / k * (self.d - k + 1)
            if abs(w_next) < self.tau:
                break
            w_standard.append(w_next)
            k += 1
            
        w_standard = np.array(w_standard)
        
        # Now apply this rolling dot product.
        # pandas rolling(window=len(w_standard)).apply is slow.
        # better use convolution.
        # np.convolve(price, w_standard) would do: sum w_standard[j] price[i-j].
        # That is exactly what we want if we don't reverse w_standard!
        # wait: np.convolve(a, v, mode='full')[n] = sum_{m} a[m] v[n-m]
        # if v = w_standard, sum a[m] w_standard[n-m].
        # let k = n-m, then m = n-k, so sum a[n-k] w_standard[k], which is correct!
        
        diffed = np.convolve(log_price.values, w_standard, mode='full')[:len(log_price)]
        diffed_series = pd.Series(diffed, index=log_price.index)
        
        # For the first len(w_standard)-1 elements, the convolution doesn't have enough history
        # We can set them to NaN.
        diffed_series.iloc[:len(w_standard)-1] = np.nan
        
        # Normalize to [0, 1]
        lookbacks = self._resolve_lookback(data, default_lookback=200)
        max_lookback = int(lookbacks.max()) if len(lookbacks) > 0 else 200
        normalizer = RollingNormalizer(window=max_lookback)
        score = normalizer.transform(diffed_series)
        
        return score
