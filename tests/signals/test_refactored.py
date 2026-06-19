import pandas as pd
import numpy as np

from src.signals.advanced_stochastic import AdvancedStochastic
from src.signals.fdi import FDI
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from src.signals.kalman_rsi import KalmanRSI
from src.signals.quantile_dema import QuantileDEMA
from src.signals.trend_strength import TrendStrengthIndex

def test_all_signals_output_minus1_1():
    # Create mock OHLCV data
    idx = pd.date_range("2025-01-01", periods=300, freq="D")
    closes = np.random.randn(300).cumsum() + 100
    opens = closes + np.random.randn(300)
    highs = np.maximum(opens, closes) + np.random.rand(300) * 5
    lows = np.minimum(opens, closes) - np.random.rand(300) * 5
    data = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.random.rand(300) * 1000
    }, index=idx)
    
    indicators = [
        AdvancedStochastic(),
        AdaptiveFourierSupertrend(),
        KalmanRSI(),
        QuantileDEMA(),
        TrendStrengthIndex()
    ]
    
    for ind in indicators:
        res = ind.compute(data)
        assert res.min() >= -1.0, f"{ind.__class__.__name__} has values < -1.0"
        assert res.max() <= 1.0, f"{ind.__class__.__name__} has values > 1.0"
