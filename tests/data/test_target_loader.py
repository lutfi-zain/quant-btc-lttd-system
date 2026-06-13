import pandas as pd
import pytest
from src.data.target_loader import load_and_forward_fill_targets, validate_target_alignment

def test_load_and_forward_fill_targets(tmp_path):
    csv_path = tmp_path / "mock_targets.csv"
    csv_path.write_text("Date,Regime\n2025-01-01,Strong Bull\n2025-01-03,Weak Bear\n")
    
    # Test basic forward fill
    y = load_and_forward_fill_targets(csv_path)
    assert len(y) == 3
    assert y.loc['2025-01-01'] == 1.0
    assert y.loc['2025-01-02'] == 1.0 # Forward filled
    assert y.loc['2025-01-03'] == 0.25
    
    # Test with custom date range
    y2 = load_and_forward_fill_targets(csv_path, start_date="2025-01-01", end_date="2025-01-05")
    assert len(y2) == 5
    assert y2.loc['2025-01-05'] == 0.25
    
def test_validate_target_alignment():
    idx = pd.date_range("2025-01-01", "2025-01-03", freq="D")
    y = pd.Series([1.0, 1.0, 0.5], index=idx)
    X = pd.DataFrame({"feat": [1, 2, 3]}, index=idx)
    
    # Should not raise
    validate_target_alignment(y, X)
    
    # Test misalignment
    X_bad = pd.DataFrame({"feat": [1, 2]}, index=idx[:2])
    with pytest.raises(ValueError, match="Target index does not match"):
        validate_target_alignment(y, X_bad)
        
    # Test NaN gaps
    y_gap = y.copy()
    y_gap.iloc[1] = None
    with pytest.raises(ValueError, match="NaN values"):
        validate_target_alignment(y_gap, X)
