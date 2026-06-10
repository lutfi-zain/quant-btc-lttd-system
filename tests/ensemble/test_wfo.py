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
        legacy_fixed_window=True,
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


def test_merge_onchain_data():
    ensemble = WFOEnsemble()

    dates_ohlcv = pd.date_range("2026-01-01", "2026-01-05", freq="D")
    ohlcv = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=dates_ohlcv)

    # On-chain data is missing for 2026-01-03
    dates_onchain = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-04"])
    onchain = pd.DataFrame({"sth_mvrv": [1.1, 1.2, 1.4]}, index=dates_onchain)

    merged = ensemble.merge_onchain_data(ohlcv, onchain)

    # Assert alignment:
    # 2026-01-03 should causally have the value from 2026-01-02 (1.2), not 2026-01-04 (1.4)
    assert merged.loc["2026-01-01", "sth_mvrv"] == 1.1
    assert merged.loc["2026-01-02", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-03", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-04", "sth_mvrv"] == 1.4
    assert merged.loc["2026-01-05", "sth_mvrv"] == 1.4


def test_purge_train_set():
    ensemble = WFOEnsemble()
    train_index = pd.date_range("2020-01-01", "2020-01-30", freq="D")
    test_intervals = [(pd.Timestamp("2020-01-15"), pd.Timestamp("2020-01-20"))]
    
    # Purge window = 3 days
    purged = ensemble.purge_train_set(train_index, test_intervals, purge_days=3)
    
    # Purge should drop 2020-01-12 to 2020-01-23 inclusive
    assert pd.Timestamp("2020-01-11") in purged
    assert pd.Timestamp("2020-01-12") not in purged
    assert pd.Timestamp("2020-01-20") not in purged
    assert pd.Timestamp("2020-01-23") not in purged
    assert pd.Timestamp("2020-01-24") in purged


def test_cpcv_split():
    ensemble = WFOEnsemble()
    dates = pd.date_range("2020-01-01", "2020-06-30", freq="D")
    df = pd.DataFrame(index=dates)
    
    splits = list(ensemble.cpcv_split(df, n_groups=6, n_test_groups=2, purge_days=5))
    
    # 6 choose 2 is 15 combinations
    assert len(splits) == 15
    for train_idx, test_idx in splits:
        # Check no intersection between train and test
        assert len(train_idx.intersection(test_idx)) == 0
        # Check that boundaries are purged (train size is reduced)
        assert len(train_idx) < len(dates) - len(test_idx)


def test_generate_wfo_folds():
    ensemble = WFOEnsemble()
    # 5 years of daily data
    dates = pd.date_range("2020-01-01", "2024-12-31", freq="D")
    
    folds = list(ensemble.generate_wfo_folds(
        dates,
        train_window_days=1095,  # 3yr
        val_window_days=180,     # 6mo
        test_window_days=180     # 6mo
    ))
    
    # There should be at least a few folds over 5 years
    assert len(folds) >= 2
    for idx, (train_idx, val_idx, test_idx) in enumerate(folds):
        # 1. Chronological order check
        assert train_idx.max() < val_idx.min()
        assert val_idx.max() < test_idx.min()
        
        # 2. Check sizes roughly correspond to specifications
        assert len(train_idx) > 1000
        assert len(val_idx) >= 170
        if idx < len(folds) - 1:
            assert len(test_idx) >= 170
        else:
            assert len(test_idx) > 0


def test_wfo_pipeline_integration():
    ensemble = WFOEnsemble()
    # 5 years of daily data
    dates = pd.date_range("2020-01-01", "2024-12-31", freq="D")
    
    np.random.seed(42)
    # Generate mock features (6 indicators)
    df_features = pd.DataFrame({
        "FDI": np.random.randn(len(dates)),
        "QuantileDEMA": np.random.randn(len(dates)),
        "AdvancedStochastic": np.random.randn(len(dates)),
        "KalmanRSI": np.random.randn(len(dates)),
        "FourierSupertrend": np.random.randn(len(dates)),
        "TrendStrengthIndex": np.random.randn(len(dates)),
        "sth_mvrv_roc_7": np.random.randn(len(dates))
    }, index=dates)
    
    # Target is binary direction
    y = (df_features["FDI"] + df_features["KalmanRSI"] > 0).astype(int)
    
    out_of_sample_scores = ensemble.run_wfo_pipeline(df_features, y)
    
    # 1. Output Final Score bounds: check they are in [-1.0, 1.0]
    assert len(out_of_sample_scores) > 0
    assert (out_of_sample_scores >= -1.0).all()
    assert (out_of_sample_scores <= 1.0).all()
    
    # 2. Verify R^2 scores are calculated and stored
    assert len(ensemble.r2_scores) > 0
    for start_date, r2 in ensemble.r2_scores.items():
        assert isinstance(r2, float)
        assert -1.0 <= r2 <= 1.0


