import numpy as np
import pandas as pd
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
    dates = pd.date_range("2024-01-01", periods=250, freq="D")
    close = pd.Series(np.random.lognormal(mean=0.01, sigma=0.02, size=250), index=dates)

    df = prepare_features_df(close, window=21)
    arr = prepare_features(close, window=21)

    # 250 daily closes. SMA 200 needs 200 days, so 199 NaNs are dropped.
    # Expected length: 250 - 199 = 51.
    assert len(df) == 51
    assert arr.shape == (51, 3) # 3 features: log_returns, realized_volatility, sma_dist
    assert list(df.columns) == ["log_returns", "realized_volatility", "sma_dist"]
    assert np.array_equal(df.values, arr)


def test_no_lookahead():
    # Make a longer series
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=250, freq="D")
    close_full = pd.Series(np.random.normal(10000, 100, 250), index=dates)

    # Cut off at 220
    close_past = close_full.iloc[:220]

    df_full = prepare_features_df(close_full, window=21)
    df_past = prepare_features_df(close_past, window=21)

    # Verify that the feature value for the 220th day is EXACTLY the same
    # regardless of whether the future data (day 221-250) was provided
    target_date = dates[219]

    assert target_date in df_full.index
    assert target_date in df_past.index

    # The feature computation must be causal
    assert np.isclose(
        df_full.loc[target_date, "realized_volatility"],
        df_past.loc[target_date, "realized_volatility"],
    )
    assert np.isclose(
        df_full.loc[target_date, "sma_dist"],
        df_past.loc[target_date, "sma_dist"],
    )
