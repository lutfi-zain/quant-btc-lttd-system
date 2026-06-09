import numpy as np
import pandas as pd
import pytest
from src.regime.hmm import train_hmm


def test_hmm_training_insufficient_data():
    # Less than 120 days of data
    close = pd.Series([10.0] * 100)
    with pytest.raises(ValueError, match="minimum 120 days required"):
        train_hmm(close)


def test_hmm_training_success_and_state_labeling():
    np.random.seed(42)
    # Generate 150 days of data with three distinct regimes:
    # 50 days BULL: positive returns, low volatility
    # 50 days BEAR: negative returns, high volatility
    # 50 days SIDEWAYS: near-zero returns, low volatility

    r_bull = np.random.normal(0.005, 0.002, 50)
    r_bear = np.random.normal(-0.01, 0.015, 50)
    r_side = np.random.normal(0.0, 0.001, 50)

    returns = np.concatenate([r_bull, r_bear, r_side])

    # Reconstruct prices from returns
    prices = [10000.0]
    for r in returns:
        prices.append(prices[-1] * np.exp(r))

    dates = pd.date_range("2024-01-01", periods=151, freq="D")
    close = pd.Series(prices, index=dates)

    model, state_to_regime = train_hmm(close, window=21)

    # Assert 3 states are mapped
    assert len(state_to_regime) == 3
    assert set(state_to_regime.values()) == {"BULL", "BEAR", "SIDEWAYS"}

    means = model.means_
    # Verify that BULL maps to highest return state
    bull_state = [k for k, v in state_to_regime.items() if v == "BULL"][0]
    bear_state = [k for k, v in state_to_regime.items() if v == "BEAR"][0]
    side_state = [k for k, v in state_to_regime.items() if v == "SIDEWAYS"][0]

    assert means[bull_state, 0] > means[bear_state, 0]
    assert means[bull_state, 0] > means[side_state, 0]
    assert means[side_state, 0] > means[bear_state, 0]

    # Verify transition matrix is valid (rows sum to 1.0)
    assert np.allclose(model.transmat_.sum(axis=1), 1.0)
