import pytest
import pandas as pd
from datetime import datetime, timezone
from src.data.pipeline import (
    standardize_and_validate,
    validate_chronological_order,
    ohlcv_pipeline,
)
from src.data.exchange_adapter import ExchangeAdapter
from src.data.db import SQLiteCache


class MockAdapter(ExchangeAdapter):
    def fetch_ohlcv(self, start_time=None, end_time=None):
        dates = pd.date_range("2024-01-01", "2024-01-05", freq="D", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [10, 11, 12, 13, 14],
                "high": [11, 12, 13, 14, 15],
                "low": [9, 10, 11, 12, 13],
                "close": [10.5, 11.5, 12.5, 13.5, 14.5],
                "volume": [100, 110, 120, 130, 140],
            },
            index=dates,
        )

        if start_time:
            df = df[df.index >= start_time]
        if end_time:
            df = df[df.index <= end_time]
        return df


def test_chronological_order_validation():
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"close": [1, 2, 3]}, index=dates)
    validate_chronological_order(df)

    df_unsorted = df.sort_index(ascending=False)
    with pytest.raises(ValueError, match="not sorted in chronological order"):
        validate_chronological_order(df_unsorted)


def test_missing_daily_bar():
    dates = [
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 3, tzinfo=timezone.utc),
    ]
    df = pd.DataFrame(
        {
            "open": [10, 12],
            "high": [11, 13],
            "low": [9, 11],
            "close": [10.5, 12.5],
            "volume": [100, 120],
        },
        index=dates,
    )

    df_std = standardize_and_validate(df)

    assert len(df_std) == 3
    assert df_std.index[1] == datetime(2024, 1, 2, tzinfo=timezone.utc)
    assert df_std.loc[df_std.index[1], "close"] == 10.5
    assert df_std.loc[df_std.index[1], "open"] == 10.5
    assert df_std.loc[df_std.index[1], "high"] == 10.5
    assert df_std.loc[df_std.index[1], "low"] == 10.5
    assert df_std.loc[df_std.index[1], "volume"] == 0.0


def test_no_lookahead():
    dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=dates)

    def causal_filter(data):
        return data["close"].shift(1)

    def non_causal_filter(data):
        return data["close"].shift(-1)

    t = datetime(2024, 1, 3, tzinfo=timezone.utc)

    df_t = df[df.index <= t]
    res_t = causal_filter(df_t)
    val_t = res_t.loc[t]

    res_all = causal_filter(df)
    val_all = res_all.loc[t]

    assert val_t == val_all, "Causal filter failed"

    res_t_non = non_causal_filter(df_t)
    val_t_non = res_t_non.loc[t]

    res_all_non = non_causal_filter(df)
    val_all_non = res_all_non.loc[t]

    assert val_t_non != val_all_non or pd.isna(val_t_non), "Non-causal filter detected"


def test_caching_behavior(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.data.pipeline.DB_PATH", db_path)
    monkeypatch.setattr("src.data.pipeline.get_exchange_adapter", lambda: MockAdapter())

    t1 = datetime(2024, 1, 3, tzinfo=timezone.utc)
    df1 = ohlcv_pipeline(end_time=t1)
    assert len(df1) == 3

    cache = SQLiteCache(db_path)
    assert cache.get_max_timestamp() == t1

    t2 = datetime(2024, 1, 5, tzinfo=timezone.utc)
    df2 = ohlcv_pipeline(end_time=t2)
    assert len(df2) == 5

    assert cache.get_max_timestamp() == t2


def test_caching_duplicate_appends(tmp_path):
    db_path = str(tmp_path / "test_dup.db")
    cache = SQLiteCache(db_path)

    dates = pd.date_range("2024-01-01", "2024-01-03", freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "volume": [100.0, 110.0, 120.0],
        },
        index=dates,
    )
    df.index.name = "timestamp"

    # First save
    cache.save_dataframe(df)

    # Save same dataframe again (should be idempotent and not raise error)
    cache.save_dataframe(df)

    # Save with modified values for existing timestamps (should update or ignore)
    df_mod = df.copy()
    df_mod.loc["2024-01-02", "close"] = 999.0
    cache.save_dataframe(df_mod)

    loaded = cache.load_dataframe()
    assert len(loaded) == 3
    # Our implementation uses INSERT OR IGNORE, so it will NOT update to 999.0
    assert loaded.loc["2024-01-02 00:00:00+00:00", "close"] == 11.5
    
    # Test update_dataframe
    cache.update_dataframe(df_mod)
    loaded_after_update = cache.load_dataframe()
    assert loaded_after_update.loc["2024-01-02 00:00:00+00:00", "close"] == 999.0
