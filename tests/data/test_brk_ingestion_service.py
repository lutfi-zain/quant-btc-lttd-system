import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.data.brk_ingestion_service import BRKIngestionService, BRKFeed, DataStaleException


def test_brk_feed_dataclass():
    feed = BRKFeed(
        sth_mvrv=1.5,
        sth_nupl=0.4,
        sth_sopr_24h=1.01,
        sth_supply_in_profit=0.8,
        stamp=datetime(2026, 6, 11, tzinfo=timezone.utc)
    )
    assert feed.sth_mvrv == 1.5
    assert feed.sth_nupl == 0.4
    assert feed.sth_sopr_24h == 1.01
    assert feed.sth_supply_in_profit == 0.8
    assert feed.stamp == datetime(2026, 6, 11, tzinfo=timezone.utc)


def test_fetch_latest(mocker):
    service = BRKIngestionService()
    
    # Mock get_series_latest to return predefined values
    latest_vals = {
        "sth_mvrv": 1.25,
        "sth_nupl": 0.35,
        "sth_sopr_24h": 0.99,
        "sth_supply_in_profit": 0.75
    }
    mocker.patch.object(service.client, "get_series_latest", side_effect=lambda name, idx: latest_vals[name])
    
    # Mock get_sync_status to return a fresh timestamp
    sync_mock = {"last_indexed_at": "2026-06-11T09:00:00Z"}
    mocker.patch.object(service.client, "get_sync_status", return_value=sync_mock)
    
    feed = service.fetch_latest()
    
    assert isinstance(feed, BRKFeed)
    assert feed.sth_mvrv == 1.25
    assert feed.sth_nupl == 0.35
    assert feed.sth_sopr_24h == 0.99
    assert feed.sth_supply_in_profit == 0.75
    assert feed.stamp == datetime(2026, 6, 11, 9, 0, 0, tzinfo=timezone.utc)


def test_validate_freshness_success():
    service = BRKIngestionService()
    current_date = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
    
    # Fresh stamp: 10 hours ago (within 24 hours)
    feed = BRKFeed(1.0, 1.0, 1.0, 1.0, current_date - timedelta(hours=10))
    # Should not raise exception
    service.validate_freshness(feed, current_date)


def test_validate_freshness_stale():
    service = BRKIngestionService()
    current_date = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
    
    # Stale stamp: 26 hours ago (more than 24 hours)
    feed = BRKFeed(1.0, 1.0, 1.0, 1.0, current_date - timedelta(hours=26))
    
    with pytest.raises(DataStaleException):
        service.validate_freshness(feed, current_date)


def test_fetch_historical(mocker):
    service = BRKIngestionService()
    
    # Mock get_series_bulk to return some dummy data
    dummy_bulk = [
        {"start": 100, "data": [1.1, 1.2, 1.3]},
        {"start": 100, "data": [0.1, 0.2, 0.3]},
        {"start": 100, "data": [1.0, 1.0, 1.0]},
        {"start": 100, "data": [0.7, 0.7, 0.7]}
    ]  # Four series bulk lists
    
    mocker.patch.object(service.client, "get_series_bulk", return_value=dummy_bulk)
    mocker.patch.object(service.client, "index_to_date", return_value=datetime(2026, 6, 8).date())
    
    df = service.fetch_historical(lookback_days=500)
    
    # Lookback should be overridden to 1200 minimum
    service.client.get_series_bulk.assert_called_once_with(
        "sth_mvrv,sth_nupl,sth_sopr_24h,sth_supply_in_profit",
        index="day1",
        start=-1200
    )
    
    assert len(df) == 3
    assert list(df.columns) == ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index[0] == pd.Timestamp("2026-06-08", tz="UTC")
