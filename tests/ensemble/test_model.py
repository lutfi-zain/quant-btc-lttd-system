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


def test_pca_consensus_ensemble():
    from src.ensemble.model import PCAConsensusEnsemble
    
    # FDI, QuantileDEMA, AdvancedStochastic, KalmanRSI, FourierSupertrend, TrendStrengthIndex
    X = pd.DataFrame({
        "FDI": [1, 1, -1],
        "QuantileDEMA": [1, -1, -1],
        "AdvancedStochastic": [1, 1, -1]
    })
    
    pca_comp_matrix = np.array([
        [0.6, 0.4, 0.692], # loadings on PC1
        [0.1, 0.8, -0.2]
    ])
    
    model = PCAConsensusEnsemble()
    model.fit(X, pca_components_matrix=pca_comp_matrix, kept_cols=["FDI", "QuantileDEMA", "AdvancedStochastic"])
    
    assert model.fitted
    assert model.weights is not None
    # Sum of absolute loadings = 0.6 + 0.4 + 0.692 = 1.692
    # weights = [0.6/1.692, 0.4/1.692, 0.692/1.692]
    
    scores = model.predict(X)
    assert len(scores) == 3
    assert (scores >= -1.0).all()
    assert (scores <= 1.0).all()
    
    # Test fallback equal weights
    model_fallback = PCAConsensusEnsemble()
    model_fallback.fit(X)
    assert model_fallback.fitted
    assert np.allclose(model_fallback.weights, [1/3, 1/3, 1/3])

