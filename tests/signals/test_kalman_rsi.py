import numpy as np
import pandas as pd
import pytest
from src.signals.kalman_rsi import KalmanRSI
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


def test_kalman_rsi_binary_constraint(dummy_ohlcv_data):
    indicator = KalmanRSI()
    scores = indicator.compute(dummy_ohlcv_data)

    assert len(scores) == len(dummy_ohlcv_data)
    assert set(scores.unique()).issubset({-1.0, 1.0})


def test_kalman_rsi_no_lookahead(dummy_ohlcv_data):
    indicator = KalmanRSI()
    for idx in [50, 100, 150, 200, 250]:
        test_no_lookahead(indicator, dummy_ohlcv_data, idx)


def test_kalman_rsi_edge_cases(dummy_ohlcv_data):
    indicator = KalmanRSI(smooth=True)
    scores = indicator.compute(dummy_ohlcv_data)
    assert len(scores) == len(dummy_ohlcv_data)
    assert set(scores.unique()).issubset({-1.0, 1.0})

    # Case: only close column
    close_only = pd.DataFrame({"close": dummy_ohlcv_data["close"]})
    scores_close = indicator.compute(close_only)
    assert len(scores_close) == len(dummy_ohlcv_data)

    # Case: empty close column raises error
    with pytest.raises(ValueError):
        indicator.compute(pd.DataFrame({"volume": [1, 2]}))


def test_kalman_rsi_dynamic_lookback(dummy_ohlcv_data):
    indicator_default = KalmanRSI()
    scores_default = indicator_default.compute(dummy_ohlcv_data)

    dyn_lookback = pd.Series(150, index=dummy_ohlcv_data.index)
    dyn_lookback.iloc[150:] = 10
    indicator = KalmanRSI(dynamic_lookback=dyn_lookback)
    scores = indicator.compute(dummy_ohlcv_data)

    assert len(scores) == len(dummy_ohlcv_data)
    assert set(scores.unique()).issubset({-1.0, 1.0})
    assert not (scores == scores_default).all(), "Dynamic lookback should change output"
    test_no_lookahead(indicator, dummy_ohlcv_data, 180)
    test_no_lookahead(indicator, dummy_ohlcv_data, 250)
