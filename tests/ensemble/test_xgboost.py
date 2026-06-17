import pytest
import pandas as pd
import numpy as np
from src.ensemble.xgboost_model import XGBoostEnsemble

def test_xgboost_ensemble():
    model = XGBoostEnsemble()
    
    # Create dummy data
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100)
    X_train = pd.DataFrame({
        "Feature1": np.random.normal(0, 1, 100),
        "Feature2": np.random.normal(0, 1, 100)
    }, index=dates)
    
    # Target is [-1.0, 1.0] depending on Feature1
    y_train = pd.Series(np.sign(X_train["Feature1"]), index=dates)
    
    model.fit(X_train, y_train)
    
    X_test = pd.DataFrame({
        "Feature1": [2.0, -2.0, 0.5, -0.5],
        "Feature2": [0.0, 0.0, 0.0, 0.0]
    }, index=pd.date_range("2020-04-10", periods=4))
    
    preds = model.predict(X_test)
    assert len(preds) == 4
    
    # Should bound between -1.0 and 1.0
    assert preds.min() >= -1.0
    assert preds.max() <= 1.0
