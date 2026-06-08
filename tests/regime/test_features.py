import numpy as np
import pandas as pd
import pytest
from src.regime.features import (
    calculate_log_returns,
    calculate_realized_volatility,
    prepare_features_df,
    prepare_features,
)

def test_calculate_log_returns():
    close = pd.Series([10.0, 11.0, 12.1])
    log_returns = calculate_log_returns(close)
    
    assert pd.isna(log_returns.iloc[0])
    assert np.isclose(log_returns.iloc[1], np.log(11.0 / 10.0))
    assert np.isclose(log_returns.iloc[2], np.log(12.1 / 11.0))

def test_calculate_realized_volatility():
    # 21-day rolling window
    # Create 25 values so we have enough for a window
    log_returns = pd.Series([0.01] * 25)
    vol = calculate_realized_volatility(log_returns, window=21)
    
    # First 20 elements should be NaN
    assert vol.iloc[:20].isna().all()
    # 21st element onwards should be calculated (and close to 0 since standard deviation of constant is 0)
    assert not vol.iloc[20:].isna().any()
    assert np.isclose(vol.iloc[20], 0.0)

def test_prepare_features():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    close = pd.Series(np.random.lognormal(mean=0.01, sigma=0.02, size=30), index=dates)
    
    df = prepare_features_df(close, window=21)
    arr = prepare_features(close, window=21)
    
    # 30 daily closes -> 29 log returns. Realized vol window of 21 needs 21 log returns.
    # Therefore, 20 rows are dropped. Expected length: 29 - 20 = 9.
    assert len(df) == 9
    assert arr.shape == (9, 2)
    assert list(df.columns) == ["log_returns", "realized_volatility"]
    assert np.array_equal(df.values, arr)

def test_no_lookahead():
    # Make a longer series
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = pd.Series(np.random.lognormal(mean=0.001, sigma=0.01, size=100), index=dates)
    
    # Let's verify causality at index t = 50
    t = dates[50]
    
    # Scenario A: Calculate features using only data up to time t
    close_truncated = close.loc[:t]
    df_truncated = prepare_features_df(close_truncated, window=21)
    val_truncated_ret = df_truncated.loc[t, "log_returns"]
    val_truncated_vol = df_truncated.loc[t, "realized_volatility"]
    
    # Scenario B: Calculate features using all data (up to index 99)
    df_full = prepare_features_df(close, window=21)
    val_full_ret = df_full.loc[t, "log_returns"]
    val_full_vol = df_full.loc[t, "realized_volatility"]
    
    # Assert values at time t are identical regardless of whether future data was available
    assert np.isclose(val_truncated_ret, val_full_ret), "Log returns calculation has lookahead bias!"
    assert np.isclose(val_truncated_vol, val_full_vol), "Realized volatility calculation has lookahead bias!"
