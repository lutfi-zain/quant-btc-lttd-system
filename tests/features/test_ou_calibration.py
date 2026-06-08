import numpy as np
import pandas as pd
import pytest
from src.features.ou_calibration import (
    estimate_ou_halflife,
    calculate_rolling_ou_halflife,
)

def test_ou_halflife_clamping_and_fallbacks():
    # 1. Test insufficient data fallback
    empty_series = pd.Series([], dtype=float)
    assert estimate_ou_halflife(empty_series, min_bars=10) == 350.0

    short_series = pd.Series([0.01, 0.02, 0.01], dtype=float)
    assert estimate_ou_halflife(short_series, min_bars=5) == 350.0

    # 2. Test b >= 1 fallback
    x_trend = np.array([1.1**i for i in range(50)])
    series_trend = pd.Series(x_trend)
    assert estimate_ou_halflife(series_trend, min_bars=30) == 350.0

    # 3. Test b <= 0 fallback or clamping
    x_osc = np.array([(-0.5)**i for i in range(50)])
    series_osc = pd.Series(x_osc)
    assert estimate_ou_halflife(series_osc, min_bars=30) == 350.0

    # 4. Test normal mean-reverting series (0 < b < 1)
    np.random.seed(42)
    x = [0.0]
    b_true = 0.5
    for _ in range(500):
        x.append(b_true * x[-1] + np.random.normal(0, 0.01))
    series_mr = pd.Series(x)
    hl = estimate_ou_halflife(series_mr, min_bars=100)
    assert hl == 120.0

    # 5. Test random walk (very long half-life, clamped to 350)
    x_rw = [0.0]
    b_true_rw = 0.999
    for _ in range(500):
        x_rw.append(b_true_rw * x_rw[-1] + np.random.normal(0, 0.01))
    series_rw = pd.Series(x_rw)
    hl_rw = estimate_ou_halflife(series_rw, min_bars=100)
    assert hl_rw == 350.0

def test_no_lookahead():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=500, freq="D")
    log_returns = pd.Series(np.random.normal(0, 0.01, size=500), index=dates)

    rolling_hl_full = calculate_rolling_ou_halflife(log_returns, window=100, min_bars=50)

    t_index = 200
    t_date = dates[t_index]

    log_returns_truncated = log_returns.iloc[:t_index + 1]
    rolling_hl_truncated = calculate_rolling_ou_halflife(log_returns_truncated, window=100, min_bars=50)

    assert rolling_hl_truncated.iloc[-1] == rolling_hl_full.iloc[t_index]
