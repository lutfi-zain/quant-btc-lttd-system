import pandas as pd
from src.backtest.wfo import WFOIterator


def test_cpcv_purging():
    # Verify absolute isolation of train and test splits mathematically
    iterator = WFOIterator(purge_days=10)
    train_index = pd.date_range("2020-01-01", "2020-01-30", freq="D")
    test_intervals = [(pd.Timestamp("2020-01-15"), pd.Timestamp("2020-01-20"))]
    
    purged = iterator.purge_train_set(train_index, test_intervals, purge_days=iterator.purge_days)
    
    # 2020-01-15 minus 10 days is 2020-01-05.
    # 2020-01-20 plus 10 days is 2020-01-30.
    # So train dates between 2020-01-05 and 2020-01-30 inclusive should be purged.
    assert pd.Timestamp("2020-01-04") in purged
    assert pd.Timestamp("2020-01-05") not in purged
    assert pd.Timestamp("2020-01-14") not in purged
    assert pd.Timestamp("2020-01-20") not in purged
    assert pd.Timestamp("2020-01-30") not in purged


def test_wfo_iterator_split():
    iterator = WFOIterator(
        train_window_days=100,
        val_window_days=10,
        test_window_days=10,
        purge_days=5
    )
    
    index = pd.date_range("2020-01-01", "2020-06-01", freq="D")
    folds = list(iterator.generate_wfo_folds(index))
    
    assert len(folds) > 0
    for train_idx, val_idx, test_idx in folds:
        # Check strict chronological order
        assert train_idx.max() < val_idx.min()
        assert val_idx.max() < test_idx.min()
        
        # Check no intersection
        assert len(train_idx.intersection(val_idx)) == 0
        assert len(val_idx.intersection(test_idx)) == 0
        assert len(train_idx.intersection(test_idx)) == 0
        
        # Check that purging occurred: the gap between train max and val min must be at least purge_days
        gap = (val_idx.min() - train_idx.max()).days
        assert gap > 5


def test_wfo_fit_predict_l1lasso_and_hmm():
    import numpy as np
    from src.ensemble.model import L1LassoEnsemble
    from src.regime.hmm import train_hmm, infer_regime_history
    
    # 1. Test L1LassoEnsemble fit and predict (L4 model)
    np.random.seed(42)
    X_train = pd.DataFrame({"PC1": np.random.randn(100), "PC2": np.random.randn(100)})
    y_train = pd.Series((X_train["PC1"] + X_train["PC2"] > 0).astype(int))
    X_test = pd.DataFrame({"PC1": np.random.randn(20), "PC2": np.random.randn(20)})
    
    model = L1LassoEnsemble()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    
    assert len(preds) == 20
    assert (preds >= -1.0).all() and (preds <= 1.0).all()
    
    # 2. Test HMM training and inference on separate splits
    # HMM requires close prices
    returns_train = np.random.normal(0.0005, 0.01, 150)
    prices_train = [10000.0]
    for r in returns_train:
        prices_train.append(prices_train[-1] * np.exp(r))
    close_train = pd.Series(prices_train, index=pd.date_range("2020-01-01", periods=151, freq="D"))
    
    # Train model on training window
    hmm_model, state_to_regime = train_hmm(close_train, window=21)
    
    # Run inference on test window (plus historical window for rolling feature computation)
    returns_test = np.random.normal(0.0002, 0.01, 50)
    prices_test = [prices_train[-1]]
    for r in returns_test:
        prices_test.append(prices_test[-1] * np.exp(r))
    
    # Create test close series (concatenated with prior close_train for feature calculation context)
    full_close = pd.concat([close_train, pd.Series(prices_test[1:], index=pd.date_range("2020-06-01", periods=50, freq="D"))])
    
    # Run inference historically
    hmm_history = infer_regime_history(hmm_model, state_to_regime, full_close, window=21)
    
    assert not hmm_history.empty
    assert "regime" in hmm_history.columns
    # Check that it computed predictions for the test portion
    test_dates = pd.date_range("2020-06-01", periods=50, freq="D")
    assert all(d in hmm_history.index for d in test_dates)


def test_point_in_time_join():
    from src.backtest.wfo import point_in_time_join
    
    dates_ohlcv = pd.date_range("2026-01-01", "2026-01-05", freq="D")
    ohlcv = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=dates_ohlcv)

    # On-chain data is missing for 2026-01-03
    onchain = pd.DataFrame({
        "sth_mvrv": [1.1, 1.2, 1.4],
        "stamp": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-04"])
    })

    merged = point_in_time_join(ohlcv, onchain)

    # Assert alignment:
    # 2026-01-03 should causally have the value from 2026-01-02 (1.2), not 2026-01-04 (1.4)
    assert merged.loc["2026-01-01", "sth_mvrv"] == 1.1
    assert merged.loc["2026-01-02", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-03", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-04", "sth_mvrv"] == 1.4
    assert merged.loc["2026-01-05", "sth_mvrv"] == 1.4


def test_no_lookahead():
    # Mathematical proof of zero index overlap using monotonic dummy arrays
    from src.backtest.wfo import WFOEngine
    engine = WFOEngine(
        train_window_days=100,
        val_window_days=10,
        test_window_days=10,
        purge_days=5
    )
    
    # 200 days of data
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    folds = list(engine.generate_wfo_folds(dates))
    
    assert len(folds) > 0
    for train_idx, val_idx, test_idx in folds:
        # Monotonicity check
        assert train_idx.is_monotonic_increasing
        assert val_idx.is_monotonic_increasing
        assert test_idx.is_monotonic_increasing
        
        # Chronological sequence assertions
        assert train_idx.max() < val_idx.min()
        assert val_idx.max() < test_idx.min()
        
        # Purging overlap check:
        # Distance between train max and val min must be > purge_days (5 days)
        gap = (val_idx.min() - train_idx.max()).days
        assert gap > 5
        
        # Verify complete set disjointness (no lookahead leakage)
        assert len(train_idx.intersection(val_idx)) == 0
        assert len(val_idx.intersection(test_idx)) == 0
        assert len(train_idx.intersection(test_idx)) == 0
