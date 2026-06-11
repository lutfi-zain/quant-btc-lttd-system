import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.pipeline import LTTDPipeline, DataStaleException
from src.data.brk_ingestion_service import BRKFeed
from src.execution.database import get_connection


@pytest.fixture
def mock_ohlcv_data():
    # Generate 1300 days of mock daily OHLCV data to support 1200 days lookback + 1095 days training
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2023-07-24", freq="D", tz="UTC")
    closes = np.cumsum(np.random.normal(0.0005, 0.01, len(dates))) + 100.0
    df = pd.DataFrame({
        "open": closes * 0.99,
        "high": closes * 1.01,
        "low": closes * 0.98,
        "close": closes,
        "volume": np.random.uniform(100, 1000, len(dates))
    }, index=dates)
    return df


@pytest.fixture
def mock_onchain_data():
    dates = pd.date_range("2020-01-01", "2023-07-24", freq="D", tz="UTC")
    np.random.seed(42)
    df = pd.DataFrame({
        "sth_mvrv": np.random.uniform(1.0, 1.8, len(dates)),
        "sth_nupl": np.random.uniform(0.1, 0.6, len(dates)),
        "sth_sopr_24h": np.random.uniform(0.98, 1.02, len(dates)),
        "sth_supply_in_profit": np.random.uniform(0.6, 0.9, len(dates))
    }, index=dates)
    return df


def test_pipeline_run_daily_success(tmp_path, mock_ohlcv_data, mock_onchain_data):
    db_path = str(tmp_path / "test_pipeline.db")
    
    # Target execution date: 2023-07-24 (last date in mock data)
    target_date = datetime(2023, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    
    # Initialize pipeline
    pipeline = LTTDPipeline(db_path=db_path)
    
    # Mock BRK Ingestion Service calls
    latest_feed = BRKFeed(
        sth_mvrv=1.5,
        sth_nupl=0.4,
        sth_sopr_24h=1.01,
        sth_supply_in_profit=0.8,
        stamp=target_date - timedelta(hours=2) # 2 hours old (fresh)
    )
    pipeline.brk_ingestion.fetch_latest = MagicMock(return_value=latest_feed)
    pipeline.brk_ingestion.fetch_historical = MagicMock(return_value=mock_onchain_data)
    
    # Mock ohlcv_pipeline
    with patch("src.pipeline.ohlcv_pipeline", return_value=mock_ohlcv_data):
        res = pipeline.run_daily(current_date=target_date)
        
        # Verify return structure
        assert res["status"] == "success"
        assert res["date"] == "2023-07-24"
        assert -1.0 <= res["final_score"] <= 1.0
        assert res["regime"] in ["BULL", "BEAR", "SIDEWAYS"]
        assert 0.0 <= res["target_exposure"] <= 1.0
        assert "posteriors" in res
        assert "indicator_scores" in res
        assert "pca_components" in res
        
        # Verify SQLite DB persistence
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_lttd WHERE date = '2023-07-24'")
            row = cursor.fetchone()
            assert row is not None
            assert row["regime"] == res["regime"]
            assert row["final_score"] == res["final_score"]
            assert row["target_exposure"] == res["target_exposure"]
            
            # Verify telemetry persistence
            cursor.execute("SELECT COUNT(*) FROM indicator_scores WHERE date = '2023-07-24'")
            assert cursor.fetchone()[0] == 6 # exactly 6 technical indicators
            
            cursor.execute("SELECT COUNT(*) FROM pca_components WHERE date = '2023-07-24'")
            assert cursor.fetchone()[0] > 0 # PCA components persisted


def test_pipeline_run_daily_stale_data(tmp_path, mock_ohlcv_data, mock_onchain_data):
    db_path = str(tmp_path / "test_pipeline_stale.db")
    target_date = datetime(2023, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    
    pipeline = LTTDPipeline(db_path=db_path)
    
    # Latest feed is 30 hours old (stale)
    stale_feed = BRKFeed(
        sth_mvrv=1.5,
        sth_nupl=0.4,
        sth_sopr_24h=1.01,
        sth_supply_in_profit=0.8,
        stamp=target_date - timedelta(hours=30)
    )
    pipeline.brk_ingestion.fetch_latest = MagicMock(return_value=stale_feed)
    pipeline.brk_ingestion.fetch_historical = MagicMock(return_value=mock_onchain_data)
    
    with patch("src.pipeline.ohlcv_pipeline", return_value=mock_ohlcv_data):
        # Should raise DataStaleException
        with pytest.raises(DataStaleException):
            pipeline.run_daily(current_date=target_date)
            
        # Verify database is empty (no daily LTTD record written)
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM daily_lttd")
            assert cursor.fetchone()[0] == 0


def test_pipeline_causality_no_lookahead(tmp_path, mock_ohlcv_data, mock_onchain_data):
    # Test that running the pipeline on a truncated dataset yields identical results to running it on the full dataset
    db_path = str(tmp_path / "test_pipeline_causality.db")
    target_date = datetime(2023, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    
    # Construct a pipeline instance for the full run
    pipeline_full = LTTDPipeline(db_path=db_path)
    latest_feed = BRKFeed(
        sth_mvrv=1.5,
        sth_nupl=0.4,
        sth_sopr_24h=1.01,
        sth_supply_in_profit=0.8,
        stamp=target_date - timedelta(hours=2)
    )
    pipeline_full.brk_ingestion.fetch_latest = MagicMock(return_value=latest_feed)
    pipeline_full.brk_ingestion.fetch_historical = MagicMock(return_value=mock_onchain_data)
    
    # 1. Run pipeline on full data
    with patch("src.pipeline.ohlcv_pipeline", return_value=mock_ohlcv_data):
        res_full = pipeline_full.run_daily(current_date=target_date)
        
    # 2. Run pipeline on truncated data (all future dates after target_date removed)
    db_path_trunc = str(tmp_path / "test_pipeline_trunc.db")
    pipeline_trunc = LTTDPipeline(db_path=db_path_trunc)
    pipeline_trunc.brk_ingestion.fetch_latest = MagicMock(return_value=latest_feed)
    
    # Truncate inputs
    mock_ohlcv_trunc = mock_ohlcv_data[mock_ohlcv_data.index <= target_date]
    mock_onchain_trunc = mock_onchain_data[mock_onchain_data.index <= target_date]
    pipeline_trunc.brk_ingestion.fetch_historical = MagicMock(return_value=mock_onchain_trunc)
    
    with patch("src.pipeline.ohlcv_pipeline", return_value=mock_ohlcv_trunc):
        res_trunc = pipeline_trunc.run_daily(current_date=target_date)
        
    # Verify outputs are exactly identical (proving lookahead bias safety)
    assert res_full["final_score"] == res_trunc["final_score"]
    assert res_full["regime"] == res_trunc["regime"]
    assert res_full["target_exposure"] == res_trunc["target_exposure"]
    assert res_full["posteriors"] == res_trunc["posteriors"]
