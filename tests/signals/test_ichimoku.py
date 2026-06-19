import numpy as np
import pandas as pd
import pytest
from src.signals.ichimoku import IchimokuCausalFilter
from tests.signals.utils import test_no_lookahead


@pytest.fixture
def dummy_ohlcv_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300)
    closes = np.cumsum(np.random.randn(300)) + 100
    highs = closes + np.random.uniform(0.5, 2.0, 300)
    lows = closes - np.random.uniform(0.5, 2.0, 300)
    opens = (highs + lows) / 2.0
    volumes = np.random.uniform(100, 1000, 300)

    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        },
        index=dates,
    )


def test_ichimoku_binary_constraint(dummy_ohlcv_data):
    indicator = IchimokuCausalFilter()
    scores = indicator.compute(dummy_ohlcv_data)

    assert len(scores) == len(dummy_ohlcv_data)
    assert scores.dropna().min() >= -1.0
    assert scores.dropna().max() <= 1.0


def test_ichimoku_no_lookahead(dummy_ohlcv_data):
    indicator = IchimokuCausalFilter()
    for idx in [100, 150, 200, 250]:
        test_no_lookahead(indicator, dummy_ohlcv_data, idx)


def test_ichimoku_edge_cases(dummy_ohlcv_data):
    indicator = IchimokuCausalFilter()

    # Empty inputs or missing columns raise error
    with pytest.raises(ValueError):
        indicator.compute(pd.DataFrame({"close": [1, 2]}))
