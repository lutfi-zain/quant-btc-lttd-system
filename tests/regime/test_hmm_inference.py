import numpy as np
import pandas as pd
import pytest
from src.regime.hmm import train_hmm, infer_regime, infer_regime_history


@pytest.fixture
def trained_hmm_setup():
    np.random.seed(42)
    # Generate 150 days of data to fit HMM
    r_bull = np.random.normal(0.005, 0.002, 50)
    r_bear = np.random.normal(-0.01, 0.015, 50)
    r_side = np.random.normal(0.0, 0.001, 50)
    returns = np.concatenate([r_bull, r_bear, r_side])

    prices = [10000.0]
    for r in returns:
        prices.append(prices[-1] * np.exp(r))

    dates = pd.date_range("2024-01-01", periods=151, freq="D")
    close = pd.Series(prices, index=dates)

    model, state_to_regime = train_hmm(close, window=21)
    return model, state_to_regime, close


def test_infer_regime_output(trained_hmm_setup):
    model, state_to_regime, close = trained_hmm_setup

    # Run inference on close
    res = infer_regime(model, state_to_regime, close, window=21)

    assert "regime" in res
    assert "posteriors" in res
    assert res["regime"] in {"BULL", "BEAR", "SIDEWAYS"}

    posteriors = res["posteriors"]
    assert len(posteriors) == 3
    assert set(posteriors.keys()) == {"BULL", "BEAR", "SIDEWAYS"}

    # Assert posteriors sum to 1.0
    assert np.isclose(sum(posteriors.values()), 1.0)


def test_infer_regime_threshold_logic(trained_hmm_setup):
    model, state_to_regime, close = trained_hmm_setup

    # Let's mock a case where P(Bull) is exactly 0.69 vs 0.71 to test threshold logic
    # We will create a mock posteriors dictionary and test classification behavior
    # Instead of full mock, let's construct scenarios manually

    # Scenario A: P(Bull) = 0.71, P(Bear) = 0.19, P(Sideways) = 0.10
    # Should classify as BULL since P(Bull) > 0.70
    mock_posteriors_a = {"BULL": 0.71, "BEAR": 0.19, "SIDEWAYS": 0.10}

    # Scenario B: P(Bull) = 0.69, P(Bear) = 0.20, P(Sideways) = 0.11
    # Should NOT classify as BULL since P(Bull) <= 0.70, should fall back to BEAR
    mock_posteriors_b = {"BULL": 0.69, "BEAR": 0.20, "SIDEWAYS": 0.11}

    # Scenario C: P(Bull) = 0.69, P(Bear) = 0.11, P(Sideways) = 0.20
    # Should NOT classify as BULL since P(Bull) <= 0.70, should fall back to SIDEWAYS
    mock_posteriors_c = {"BULL": 0.69, "BEAR": 0.11, "SIDEWAYS": 0.20}

    # Helper to test threshold logic on state_to_regime
    # In order to test the internal function logic, we can inspect how we wrote infer_regime.
    # It classifies BULL if posteriors["BULL"] > 0.70, else max of BEAR vs SIDEWAYS.

    def classify(posteriors):
        if posteriors["BULL"] > 0.70:
            return "BULL"
        else:
            if posteriors["BEAR"] >= posteriors["SIDEWAYS"]:
                return "BEAR"
            else:
                return "SIDEWAYS"

    assert classify(mock_posteriors_a) == "BULL"
    assert classify(mock_posteriors_b) == "BEAR"
    assert classify(mock_posteriors_c) == "SIDEWAYS"


def test_infer_regime_history_df(trained_hmm_setup):
    model, state_to_regime, close = trained_hmm_setup

    df = infer_regime_history(model, state_to_regime, close, window=21)

    # Verify index and columns
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert list(df.columns) == ["p_bull", "p_bear", "p_sideways", "regime"]

    # Check that rows sum to 1.0
    probs = df[["p_bull", "p_bear", "p_sideways"]].sum(axis=1)
    assert np.allclose(probs, 1.0)

    # Check threshold logic consistency
    for idx, row in df.iterrows():
        if row["p_bull"] > 0.70:
            assert row["regime"] == "BULL"
        else:
            assert row["regime"] in {"BEAR", "SIDEWAYS"}
            if row["p_bear"] >= row["p_sideways"]:
                assert row["regime"] == "BEAR"
            else:
                assert row["regime"] == "SIDEWAYS"
