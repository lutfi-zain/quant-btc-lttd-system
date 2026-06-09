import pandas as pd
import numpy as np
import pytest
from src.signals.quantile_dema import QuantileDEMA
from tests.signals.utils import test_no_lookahead


@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500)
    closes = np.cumsum(np.random.randn(500)) + 100
    return pd.DataFrame({"close": closes}, index=dates)


def test_quantile_dema_functionality(sample_data):
    indicator = QuantileDEMA(dema_span=50)
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    assert len(signals) == len(sample_data)
    unique_vals = set(signals.dropna().unique())
    assert unique_vals.issubset({-1.0, 1.0})


def test_quantile_dema_no_lookahead(sample_data):
    indicator = QuantileDEMA(dema_span=50)
    test_no_lookahead(indicator, sample_data, 250)
    test_no_lookahead(indicator, sample_data, 400)


def test_quantile_dema_dynamic_lookback(sample_data):
    dyn_lookback = pd.Series(150, index=sample_data.index)
    dyn_lookback.iloc[250:] = 300
    indicator = QuantileDEMA(dynamic_lookback=dyn_lookback, dema_span=50)
    signals = indicator.compute(sample_data)

    assert isinstance(signals, pd.Series)
    test_no_lookahead(indicator, sample_data, 200)
    test_no_lookahead(indicator, sample_data, 350)
