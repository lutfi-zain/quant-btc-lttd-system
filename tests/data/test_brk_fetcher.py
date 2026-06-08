import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

from src.data.brk_fetcher import BRKDataFetcher, StaleOnChainDataError

def test_fetch_latest_success(mocker):
    fetcher = BRKDataFetcher()
    mocker.patch.object(fetcher.client, 'get_series_latest', return_value=0.85)
    
    current = datetime.now(timezone.utc)
    status_mock = {"last_indexed_at": current.strftime("%Y-%m-%dT%H:%M:%SZ")}
    mocker.patch.object(fetcher.client, 'get_sync_status', return_value=status_mock)
    
    res = fetcher.fetch_latest("sth_mvrv")
    assert res["value"] == 0.85
    assert res["stamp"] == current.replace(microsecond=0)

def test_fetch_latest_stale_raises_error(mocker):
    fetcher = BRKDataFetcher()
    mocker.patch.object(fetcher.client, 'get_series_latest', return_value=0.85)
    
    stale_date = datetime.now(timezone.utc) - timedelta(days=2)
    status_mock = {"last_indexed_at": stale_date.strftime("%Y-%m-%dT%H:%M:%SZ")}
    mocker.patch.object(fetcher.client, 'get_sync_status', return_value=status_mock)
    
    with pytest.raises(StaleOnChainDataError):
        fetcher.fetch_latest("sth_mvrv")

def test_fetch_historical_bulk(mocker):
    fetcher = BRKDataFetcher()
    bulk_mock = [{"index": "day1", "data": [1, 2, 3]}]
    mocker.patch.object(fetcher.client, 'get_series_bulk', return_value=bulk_mock)
    
    res = fetcher.fetch_historical_bulk(["sth_mvrv"], start=-3)
    assert res == bulk_mock
    fetcher.client.get_series_bulk.assert_called_once_with(["sth_mvrv"], index="day1", start=-3)

def test_no_lookahead():
    # Test align_with_ohlcv for causal alignment
    fetcher = BRKDataFetcher()
    
    dates = pd.date_range("2026-01-01", "2026-01-05", tz="UTC")
    ohlcv_df = pd.DataFrame({"close": [10, 20, 30, 40, 50]}, index=dates)
    
    # BRK data missing for 2026-01-03
    brk_dates = [pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-02", tz="UTC"), pd.Timestamp("2026-01-04", tz="UTC")]
    brk_df = pd.DataFrame({"sth_mvrv": [1.1, 1.2, 1.4]}, index=brk_dates)
    
    merged = fetcher.align_with_ohlcv(brk_df, ohlcv_df)
    
    # 2026-01-01 should be 1.1
    # 2026-01-02 should be 1.2
    # 2026-01-03 should be 1.2 (forward filled from 01-02)
    # 2026-01-04 should be 1.4
    # 2026-01-05 should be 1.4 (forward filled from 01-04)
    
    assert merged.loc["2026-01-01", "sth_mvrv"] == 1.1
    assert merged.loc["2026-01-02", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-03", "sth_mvrv"] == 1.2
    assert merged.loc["2026-01-04", "sth_mvrv"] == 1.4
    assert merged.loc["2026-01-05", "sth_mvrv"] == 1.4
    
    # Ensure no lookahead by verifying 2026-01-03 does NOT equal 1.4
    assert merged.loc["2026-01-03", "sth_mvrv"] != 1.4
