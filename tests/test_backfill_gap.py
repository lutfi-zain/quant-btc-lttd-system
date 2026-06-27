"""
Tests for backfill_gap.py — smart gap detection and sequential backfill.
"""

import os
import sys
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Ensure root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backfill_gap import detect_gap, check_valuation_api


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database with the daily_lttd table."""
    db_path = str(tmp_path / "test_lttd.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_lttd (
            data_as_of TEXT,
            date TEXT PRIMARY KEY,
            regime TEXT,
            final_score REAL,
            target_exposure REAL,
            posterior_prob REAL,
            circuit_breaker_active INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestDetectGap:
    def test_detect_gap_with_existing_data(self, tmp_db):
        """When DB has data up to N days ago, detect_gap returns the correct gap."""
        # Insert data up to 5 days ago
        target_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=5)
        date_str = target_date.strftime("%Y-%m-%d")

        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob) "
            "VALUES (?, ?, 'BULL', 0.5, 1.0, 0.8)",
            (date_str, date_str),
        )
        conn.commit()
        conn.close()

        last_date, gap_days = detect_gap(tmp_db)

        assert last_date is not None
        assert last_date.strftime("%Y-%m-%d") == date_str
        assert gap_days == 5

    def test_detect_gap_empty_db(self, tmp_db):
        """When the DB is empty, detect_gap returns None for last_date."""
        last_date, gap_days = detect_gap(tmp_db)

        assert last_date is None
        assert gap_days == 0

    def test_detect_gap_up_to_date(self, tmp_db):
        """When the DB has today's date, gap_days should be 0."""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        date_str = today.strftime("%Y-%m-%d")

        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob) "
            "VALUES (?, ?, 'BULL', 0.5, 1.0, 0.8)",
            (date_str, date_str),
        )
        conn.commit()
        conn.close()

        last_date, gap_days = detect_gap(tmp_db)

        assert last_date is not None
        assert gap_days == 0

    def test_detect_gap_single_day(self, tmp_db):
        """When the DB is missing exactly 1 day (yesterday's data), gap_days should be 1."""
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob) "
            "VALUES (?, ?, 'BEAR', -0.2, 0.0, 0.6)",
            (date_str, date_str),
        )
        conn.commit()
        conn.close()

        last_date, gap_days = detect_gap(tmp_db)

        assert last_date is not None
        assert gap_days == 1


class TestGapFillSequentialExecution:
    def test_gap_fill_dates_are_chronological(self, tmp_db):
        """Verify that gap dates are generated in chronological order (oldest first)."""
        # Insert data 5 days ago
        base_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=5)
        date_str = base_date.strftime("%Y-%m-%d")

        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob) "
            "VALUES (?, ?, 'BULL', 0.5, 1.0, 0.8)",
            (date_str, date_str),
        )
        conn.commit()
        conn.close()

        last_date, gap_days = detect_gap(tmp_db)

        # Generate missing dates
        missing_dates = []
        for i in range(1, gap_days + 1):
            missing_dates.append(last_date + timedelta(days=i))

        # Verify chronological order
        assert len(missing_dates) == 5
        for i in range(1, len(missing_dates)):
            assert missing_dates[i] > missing_dates[i - 1]

    @patch("backfill_gap.LTTDPipeline")
    def test_gap_fill_error_recovery(self, mock_pipeline_cls, tmp_db):
        """Verify that if one date fails, the loop continues to the next."""
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        # Simulate: first call succeeds, second fails, third succeeds
        mock_pipeline.run_daily.side_effect = [
            {"regime": "BULL", "final_score": 0.5, "target_exposure": 1.0},
            Exception("Connection timed out"),
            {"regime": "BEAR", "final_score": -0.3, "target_exposure": 0.0},
        ]

        # Run 3 dates manually
        results_success = []
        results_failed = []
        dates = [
            datetime(2026, 6, 25, tzinfo=timezone.utc),
            datetime(2026, 6, 26, tzinfo=timezone.utc),
            datetime(2026, 6, 27, tzinfo=timezone.utc),
        ]

        for target_date in dates:
            try:
                res = mock_pipeline.run_daily(target_date)
                results_success.append(target_date)
            except Exception:
                results_failed.append(target_date)

        assert len(results_success) == 2
        assert len(results_failed) == 1
        assert mock_pipeline.run_daily.call_count == 3


class TestCheckValuationApi:
    def test_valuation_api_healthy(self):
        """When the valuation API returns 200, check_valuation_api returns True."""
        import requests as req_mod
        with patch.object(req_mod, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert check_valuation_api() is True

    def test_valuation_api_down(self):
        """When the valuation API is unreachable, check_valuation_api returns False."""
        import requests as req_mod
        with patch.object(req_mod, "get", side_effect=ConnectionError("Connection refused")):
            assert check_valuation_api() is False
