import pandas as pd
import numpy as np
import pytest
from src.signals.advanced_stochastic import AdvancedStochastic
from tests.signals.utils import test_no_lookahead


@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500)
    closes = np.cumsum(np.random.randn(500)) + 100
    highs = closes + np.random.rand(500) * 2.0
    lows = closes - np.random.rand(500) * 2.0
    return pd.DataFrame({"close": closes, "high": highs, "low": lows}, index=dates)


def test_stochastic_functionality(sample_data):
    indicator = AdvancedStochastic()
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    assert len(signals) == len(sample_data)
    assert signals.dropna().min() >= 0.0
    assert signals.dropna().max() <= 1.0


def test_stochastic_no_lookahead(sample_data):
    indicator = AdvancedStochastic()
    test_no_lookahead(indicator, sample_data, 250)
    test_no_lookahead(indicator, sample_data, 400)


def test_stochastic_dynamic_lookback(sample_data):
    dyn_lookback = pd.Series(150, index=sample_data.index)
    dyn_lookback.iloc[250:] = 300
    indicator = AdvancedStochastic(dynamic_lookback=dyn_lookback)
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    test_no_lookahead(indicator, sample_data, 200)
    test_no_lookahead(indicator, sample_data, 350)
