import pandas as pd
import numpy as np

from src.signals.advanced_stochastic import AdvancedStochastic
from src.signals.fdi import FDI
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from src.signals.kalman_rsi import KalmanRSI
from src.signals.quantile_dema import QuantileDEMA
from src.signals.trend_strength import TrendStrengthIndex

def test_all_signals_output_0_1():
    # Create mock OHLCV data
    idx = pd.date_range("2025-01-01", periods=300, freq="D")
    data = pd.DataFrame({
        "open": np.random.randn(300).cumsum() + 100,
        "high": np.random.randn(300).cumsum() + 105,
        "low": np.random.randn(300).cumsum() + 95,
        "close": np.random.randn(300).cumsum() + 100,
        "volume": np.random.rand(300) * 1000
    }, index=idx)
    
    indicators = [
        AdvancedStochastic(),
        FDI(),
        AdaptiveFourierSupertrend(),
        KalmanRSI(),
        QuantileDEMA(),
        TrendStrengthIndex()
    ]
    
    for ind in indicators:
        res = ind.compute(data)
        assert res.min() >= 0.0, f"{ind.__class__.__name__} has values < 0.0"
        assert res.max() <= 1.0, f"{ind.__class__.__name__} has values > 1.0"
