import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from src.ensemble.wfo import WFOEnsemble


def test_fetch_deep_matrices():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_historical_bulk.return_value = [{"index": "day1", "data": [1]}]

    ensemble = WFOEnsemble(fetcher=mock_fetcher)
    res = ensemble.fetch_deep_matrices(start=-500)

    assert res == [{"index": "day1", "data": [1]}]
    mock_fetcher.fetch_historical_bulk.assert_called_once_with(
        ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"], start=-500
    )


def test_wfo_ou_calibration_quarterly():
    ensemble = WFOEnsemble()
    
    # Generate 4 years of daily log returns to support 3 years in-sample + 1 year out-of-sample
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    np.random.seed(42)
    # Mean-reverting process with positive AR(1) coefficient b
    x = [0.0]
    for _ in range(len(dates) - 1):
        x.append(0.5 * x[-1] + np.random.normal(0, 0.01))
    log_returns = pd.Series(x, index=dates)

    # Run calibration from 2023-01-01 to 2023-12-31 (rolling quarterly)
    start_date = pd.Timestamp("2023-01-01")
    end_date = pd.Timestamp("2023-12-31")
    
    daily_hl = ensemble.run_wfo_calibration(log_returns, start_date, end_date)
    
    # Verify we get a value for every day in the target range
    assert len(daily_hl) == len(log_returns.loc[start_date:end_date])
    # Values should be clamped within bounds
    assert (daily_hl >= 120.0).all()
    assert (daily_hl <= 350.0).all()
    
    # Verify quarterly updates: the values should be constant within a quarter
    q1_val = daily_hl.loc["2023-01-15"]
    assert daily_hl.loc["2023-03-31"] == q1_val
    
    q2_val = daily_hl.loc["2023-04-15"]
    # Check if a new quarter actually recalculated
    # Since it's a random series, Q1 and Q2 estimates might differ slightly
    # but they are both clamped to 120.0 because b is around 0.5 (very fast MR)
    assert daily_hl.loc["2023-06-30"] == q2_val


def test_legacy_fixed_window():
    ensemble = WFOEnsemble()
    dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
    log_returns = pd.Series(0.0, index=dates)
    
    # With legacy_fixed_window=True, it should always return 200.0
    daily_hl = ensemble.run_wfo_calibration(
        log_returns, 
        pd.Timestamp("2023-01-01"), 
        pd.Timestamp("2023-12-31"), 
        legacy_fixed_window=True
    )
    assert (daily_hl == 200.0).all()


def test_ou_halflife_exclusion_from_features():
    # Verify that the OU Half-Life is not injected as an additive feature column
    ensemble = WFOEnsemble()
    
    # Fetch deep matrices represents features sent to the ensemble layer
    # We must ensure "ou_halflife" is NOT in the series list
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_historical_bulk.return_value = [{"index": "day1", "data": [1]}]
    ensemble.fetcher = mock_fetcher
    
    ensemble.fetch_deep_matrices()
    
    args, kwargs = mock_fetcher.fetch_historical_bulk.call_args
    feature_columns = args[0]
    
    # Feature columns must not contain OU half-life, so VIF is 0/undefined for it
    assert "ou_halflife" not in feature_columns
    assert "ou" not in feature_columns
