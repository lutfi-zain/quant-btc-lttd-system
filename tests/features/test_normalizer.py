import pandas as pd
import numpy as np
from src.features.normalizer import RollingNormalizer

def test_rolling_normalizer_bounds():
    norm = RollingNormalizer(window=5)
    s = pd.Series([10, 20, 30, 40, 50, 60, 70])
    
    out = norm.transform(s)
    
    # Check that all outputs are bounded between 0 and 1
    assert out.min() >= 0.0
    assert out.max() <= 1.0

def test_no_lookahead():
    """
    Ensures that adding future data points does not change the normalized
    value of past data points.
    """
    norm = RollingNormalizer(window=5)
    
    # Base dataset
    s1 = pd.Series([10, 20, 15, 30, 25], index=pd.date_range("2025-01-01", periods=5))
    out1 = norm.transform(s1)
    
    # Dataset with future points appended
    s2 = pd.Series([10, 20, 15, 30, 25, 100, 5], index=pd.date_range("2025-01-01", periods=7))
    out2 = norm.transform(s2)
    
    # The first 5 outputs MUST be perfectly identical
    pd.testing.assert_series_equal(out1, out2.iloc[:5])
    
def test_constant_value_fallback():
    norm = RollingNormalizer(window=5)
    s = pd.Series([10, 10, 10])
    out = norm.transform(s)
    
    # Should fallback to 0.5 when there is no variance
    assert (out == 0.5).all()
