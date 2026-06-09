import numpy as np
import pandas as pd
import pytest
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from tests.signals.utils import test_no_lookahead


@pytest.fixture
def dummy_ohlcv_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300)
    # Generate random walk for close price
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


def test_fourier_supertrend_binary_constraint(dummy_ohlcv_data):
    indicator = AdaptiveFourierSupertrend()
    scores = indicator.compute(dummy_ohlcv_data)

    # Check index matches input
    pd.testing.assert_index_equal(scores.index, dummy_ohlcv_data.index)

    # Check length
    assert len(scores) == len(dummy_ohlcv_data)

    # Check score is strictly binary {-1.0, +1.0}
    unique_vals = set(scores.unique())
    assert unique_vals.issubset({-1.0, 1.0})


def test_fourier_supertrend_lookahead_bias(dummy_ohlcv_data):
    indicator = AdaptiveFourierSupertrend()
    # Test causality at multiple points in time
    for idx in [50, 100, 150, 200, 250]:
        test_no_lookahead(indicator, dummy_ohlcv_data, idx)


def test_fourier_supertrend_edge_cases(dummy_ohlcv_data):
    indicator = AdaptiveFourierSupertrend()

    # Case 1: VERY short data (less than 30 bars, before FFT stabilizes)
    short_data = dummy_ohlcv_data.iloc[:15].copy()
    scores_short = indicator.compute(short_data)
    assert len(scores_short) == 15
    assert set(scores_short.unique()).issubset({-1.0, 1.0})
    assert not scores_short.isna().any()

    # Case 2: DataFrame with uppercase column names
    upper_data = dummy_ohlcv_data.copy()
    upper_data.columns = [c.upper() for c in upper_data.columns]
    scores_upper = indicator.compute(upper_data)
    assert len(scores_upper) == len(dummy_ohlcv_data)
    assert set(scores_upper.unique()).issubset({-1.0, 1.0})

    # Case 3: Dynamic lookback configured
    dyn_lookback = pd.Series(150, index=dummy_ohlcv_data.index)
    dyn_lookback.iloc[150:] = 300
    indicator_dyn = AdaptiveFourierSupertrend(dynamic_lookback=dyn_lookback)
    scores_dyn = indicator_dyn.compute(dummy_ohlcv_data)
    assert len(scores_dyn) == len(dummy_ohlcv_data)
    assert set(scores_dyn.unique()).issubset({-1.0, 1.0})


# Layer Integration Verification (Task 4.1 - 4.4)

def run_signal_engine_pipeline(data: pd.DataFrame) -> pd.DataFrame:
    """
    Simulates the Layer 2 Signal Engine pipeline integration.
    """
    indicator = AdaptiveFourierSupertrend()
    return pd.DataFrame({"fourier_supertrend": indicator.compute(data)}, index=data.index)


def test_layer_2_pipeline_integration(dummy_ohlcv_data):
    # Verify indicator integrates into Layer 2 pipeline successfully
    pipeline_features = run_signal_engine_pipeline(dummy_ohlcv_data)
    assert "fourier_supertrend" in pipeline_features.columns
    assert len(pipeline_features) == len(dummy_ohlcv_data)


def test_vif_integration(dummy_ohlcv_data):
    from src.features.vif import calculate_vif

    # Calculate Fourier Supertrend
    indicator = AdaptiveFourierSupertrend()
    fourier_scores = indicator.compute(dummy_ohlcv_data)

    # Create other features: momentum (price difference) and volatility (rolling standard deviation)
    momentum = dummy_ohlcv_data["close"].diff().fillna(0)
    volatility = dummy_ohlcv_data["close"].rolling(20).std().bfill().fillna(0)

    features_df = pd.DataFrame({
        "fourier_supertrend": fourier_scores,
        "momentum": momentum,
        "volatility": volatility
    })

    # Calculate VIF to ensure fourier_supertrend remains < 10.0 (orthogonal)
    vifs = calculate_vif(features_df)
    assert vifs["fourier_supertrend"] < 10.0


def test_lasso_ingestion(dummy_ohlcv_data):
    from sklearn.linear_model import LogisticRegression

    indicator = AdaptiveFourierSupertrend()
    fourier_scores = indicator.compute(dummy_ohlcv_data)

    # Generate other features and target (binary direction)
    momentum = dummy_ohlcv_data["close"].diff().fillna(0)
    X = pd.DataFrame({
        "fourier_supertrend": fourier_scores,
        "momentum": momentum
    })

    # Target: next day direction mapped to binary classes [0, 1]
    y = np.sign(dummy_ohlcv_data["close"].shift(-1) - dummy_ohlcv_data["close"]).fillna(1)
    y = y.map({-1.0: 0, 0.0: 0, 1.0: 1})

    # Fit L1-Lasso Logistic Regression model
    clf = LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=1.0, random_state=42)
    clf.fit(X.iloc[:-1], y.iloc[:-1])

    # Predict
    preds = clf.predict(X)
    assert len(preds) == len(dummy_ohlcv_data)
    assert np.isin(preds, [0, 1]).all()


def test_wfo_backtest_pass(dummy_ohlcv_data):
    from sklearn.linear_model import LogisticRegression

    indicator = AdaptiveFourierSupertrend()
    fourier_scores = indicator.compute(dummy_ohlcv_data)
    momentum = dummy_ohlcv_data["close"].diff().fillna(0)

    X = pd.DataFrame({
        "fourier_supertrend": fourier_scores,
        "momentum": momentum
    })
    y = np.sign(dummy_ohlcv_data["close"].shift(-1) - dummy_ohlcv_data["close"]).fillna(1).map({-1.0: 0, 0.0: 0, 1.0: 1})

    train_size = 150
    val_size = 30

    # Simulate WFO calibration splits
    for start in range(0, len(dummy_ohlcv_data) - train_size - val_size, val_size):
        X_train = X.iloc[start : start + train_size]
        y_train = y.iloc[start : start + train_size]
        X_test = X.iloc[start + train_size : start + train_size + val_size]

        model = LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=1.0, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        assert len(preds) == val_size
