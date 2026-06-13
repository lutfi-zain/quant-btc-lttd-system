import pandas as pd
import numpy as np
import pytest
from src.signals.fdi import FDI
from tests.signals.utils import test_no_lookahead


@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500)
    # Generate daily price series
    closes = np.cumsum(np.random.randn(500)) + 100
    return pd.DataFrame({"close": closes}, index=dates)


def test_fdi_functionality(sample_data):
    indicator = FDI(ema_span=50)
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    assert len(signals) == len(sample_data)
    # Outputs must be standardized to {-1, +1}
    assert signals.dropna().min() >= 0.0
    assert signals.dropna().max() <= 1.0


def test_fdi_no_lookahead(sample_data):
    indicator = FDI(ema_span=50)
    # FDI has lookback resolving to 200, so start lookahead checks later in the series
    test_no_lookahead(indicator, sample_data, 250)
    test_no_lookahead(indicator, sample_data, 400)


def test_fdi_dynamic_lookback(sample_data):
    # Construct a dynamic lookback series
    dyn_lookback = pd.Series(150, index=sample_data.index)
    dyn_lookback.iloc[250:] = 300
    indicator = FDI(dynamic_lookback=dyn_lookback, ema_span=50)
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    # Test lookahead with dynamic window
    test_no_lookahead(indicator, sample_data, 200)
    test_no_lookahead(indicator, sample_data, 350)
