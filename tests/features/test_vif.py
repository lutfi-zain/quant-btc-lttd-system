import pandas as pd
import numpy as np
from src.features.vif import (
    calculate_vif,
    pratt_measure,
    prune_multicollinear_indicators,
)


def test_vif_calculation():
    np.random.seed(42)
    x1 = np.random.randn(100)
    # x2 is highly correlated with x1
    x2 = x1 + np.random.normal(0, 0.05, 100)
    # x3 is independent
    x3 = np.random.randn(100)

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
    vifs = calculate_vif(df)

    # x1 and x2 should have high VIF (> 10)
    assert vifs["x1"] > 10.0
    assert vifs["x2"] > 10.0
    # x3 should have low VIF (~1.0)
    assert vifs["x3"] < 2.0


def test_pratt_measure():
    np.random.seed(42)
    # Simple linear relationship: y = 2*x1 + 0.5*x2 + noise
    x1 = np.random.randn(100)
    x2 = np.random.randn(100)
    y = 2.0 * x1 + 0.5 * x2 + np.random.normal(0, 0.1, 100)

    X = pd.DataFrame({"x1": x1, "x2": x2})
    pratt = pratt_measure(X, y)

    # Pratt's measure for x1 should be higher than x2 since beta is larger
    assert pratt["x1"] > pratt["x2"]
    # Sum of Pratt's measures should be approximately 1.0 (relative shares of R^2)
    assert np.isclose(pratt.sum(), 1.0, atol=0.05)


def test_vif_pruning():
    np.random.seed(42)
    x1 = np.random.randn(100)
    # Collinear pair 1
    x2 = x1 + np.random.normal(0, 0.01, 100)
    # Collinear pair 2
    x3 = x1 + np.random.normal(0, 0.02, 100)
    # Independent feature that is highly predictive
    x4 = np.random.randn(100)

    y = 5.0 * x4 + 0.5 * x1 + np.random.normal(0, 0.1, 100)

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4})

    # Prune with VIF threshold = 10
    pruned_df = prune_multicollinear_indicators(df, y, vif_threshold=10.0)

    # Check that high VIF features were pruned
    vifs = calculate_vif(pruned_df)
    assert (vifs <= 10.0).all()
    # x4 should definitely be kept because it is highly predictive and independent
    assert "x4" in pruned_df.columns
    # Only one of the collinear group (x1, x2, x3) should be left (or they should be pruned to satisfy VIF <= 10)
    collinear_count = sum([col in pruned_df.columns for col in ["x1", "x2", "x3"]])
    assert collinear_count <= 1
