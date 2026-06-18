import pandas as pd
import numpy as np
import pytest
from src.data.target_loader import load_regime_targets, validate_target_alignment, compute_forward_returns_target

def test_compute_forward_returns_target():
    # Generate mock close prices (300 days)
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=300, freq="D")
    closes = pd.Series(np.exp(np.cumsum(np.random.normal(0.001, 0.01, 300))), index=dates)
    
    target = compute_forward_returns_target(closes)
    
    # Verify shape and type
    assert isinstance(target, pd.Series)
    assert len(target) == 300
    
    # Check freshness constraint: target for last 21 days must be NaN
    assert target.iloc[-21:].isnull().all()
    
    # Check that historical targets (up to t-21) are calculated
    assert not target.iloc[:-21].isnull().any()
    
    # Check values are clipped to [-1.0, 1.0]
    assert (target.dropna() >= -1.0).all()
    assert (target.dropna() <= 1.0).all()
    
    # Z-score properties (mean should be close to 0, std should be close to 1)
    mean_val = target.dropna().mean()
    std_val = target.dropna().std()
    assert abs(mean_val) < 0.5
    assert 0.5 <= std_val <= 1.5

def test_load_regime_targets():
    dates = pd.date_range("2025-01-01", periods=100, freq="D")
    closes = pd.Series(np.exp(np.cumsum(np.random.normal(0.001, 0.01, 100))), index=dates)
    
    y = load_regime_targets(dates, close_series=closes)
    
    assert len(y) == 100
    assert y.index.equals(dates)
    assert y.iloc[-21:].isnull().all()

def test_validate_target_alignment():
    idx = pd.date_range("2025-01-01", periods=50, freq="D")
    # Last 21 rows are NaN, rest are valid floats
    vals = [0.5] * 29 + [np.nan] * 21
    y = pd.Series(vals, index=idx)
    X = pd.DataFrame({"feat": [1] * 50}, index=idx)
    
    # Valid alignment should not raise
    validate_target_alignment(y, X)
    
    # Target index misalignment
    X_bad = pd.DataFrame({"feat": [1] * 40}, index=idx[:40])
    with pytest.raises(ValueError, match="Target index does not match"):
        validate_target_alignment(y, X_bad)
        
    # Historical NaN gap (excluding the last 21 rows)
    y_bad = y.copy()
    y_bad.iloc[5] = np.nan
    with pytest.raises(ValueError, match="Target series contains NaN values"):
        validate_target_alignment(y_bad, X)
