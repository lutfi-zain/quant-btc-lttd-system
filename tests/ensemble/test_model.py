import numpy as np
import pandas as pd
import pytest
from src.ensemble.model import L1LassoEnsemble


def test_model_fit_and_score_bounds():
    np.random.seed(42)
    # Generate mock features and target
    X = pd.DataFrame({
        "PC1": np.random.randn(100),
        "PC2": np.random.randn(100)
    })
    # Target is binary 0 or 1
    y = (X["PC1"] + X["PC2"] > 0).astype(int)

    model = L1LassoEnsemble()
    model.fit(X, y)
    
    # Assert model is fitted
    assert model.fitted

    # Predict scores
    scores = model.predict_score(X)
    
    assert len(scores) == 100
    # Check bounds
    assert (scores >= -1.0).all()
    assert (scores <= 1.0).all()


def test_model_pratt_measure():
    np.random.seed(42)
    x1 = np.random.randn(150)
    x2 = np.random.randn(150)
    # target is linearly dependent on x1 and x2
    y = 2.0 * x1 + 0.5 * x2 + np.random.normal(0, 0.1, 150)
    
    X = pd.DataFrame({"x1": x1, "x2": x2})

    model = L1LassoEnsemble()
    model.fit(X, (y > 0).astype(int)) # fit binary target for logistic regression
    
    # Calculate Pratt's measure relative to continuous target y
    pratt = model.calculate_pratt(X, y)
    
    assert np.isclose(pratt.sum(), 1.0, atol=0.05)
    assert pratt["x1"] > pratt["x2"]
