import pytest
import sqlite3
import json
from unittest.mock import MagicMock
from src.execution.engine import ExecutionEngine
from src.data.brk_fetcher import StaleOnChainDataError
from src.execution.database import init_db, get_connection


def test_run_daily_success():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 0.8,
        "stamp": "2026-06-08",
    }

    engine = ExecutionEngine(fetcher=mock_fetcher)
    res = engine.run_daily()

    assert res["status"] == "success"
    assert res["metrics"]["mvrv"] == 0.8
    assert res["metrics"]["nupl"] == 0.8


def test_run_daily_stale():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = StaleOnChainDataError("Stale data")

    engine = ExecutionEngine(fetcher=mock_fetcher)
    res = engine.run_daily()

    assert res["status"] == "paused"
    assert "Stale data" in res["error"]


def test_persist_features(tmp_path):
    db_path = str(tmp_path / "test_engine_persist.db")
    init_db(db_path)

    engine = ExecutionEngine()
    engine.persist_features(
        date_str="2023-01-01",
        indicator_scores={"rsi": 1, "macd": -1},
        pca_components={"PC1": 0.5, "PC2": -0.3},
        db_path=db_path
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indicator_scores WHERE date = '2023-01-01' ORDER BY indicator_name")
        rows_ind = cursor.fetchall()
        assert len(rows_ind) == 2
        assert rows_ind[0]["indicator_name"] == "macd"
        assert rows_ind[0]["score"] == -1
        assert rows_ind[1]["indicator_name"] == "rsi"
        assert rows_ind[1]["score"] == 1

        cursor.execute("SELECT * FROM pca_components WHERE date = '2023-01-01' ORDER BY component_name")
        rows_pca = cursor.fetchall()
        assert len(rows_pca) == 2
        assert rows_pca[0]["component_name"] == "PC1"
        assert rows_pca[0]["value"] == 0.5
        assert rows_pca[1]["component_name"] == "PC2"
        assert rows_pca[1]["value"] == -0.3


def test_engine_run_pipeline_multiday(tmp_path):
    db_path = str(tmp_path / "test_multiday_pipeline.db")
    init_db(db_path)

    engine = ExecutionEngine()

    # Day 1: BULL regime
    day1_res = engine.run(
        date_str="2026-06-01",
        final_score=0.8,
        regime="BULL",
        posteriors={"BULL": 0.9, "BEAR": 0.05, "SIDEWAYS": 0.05},
        log_return=0.01,
        realized_volatility=0.12,
        db_path=db_path
    )
    assert day1_res["status"] == "success"
    assert day1_res["target_exposure"] == 0.8
    assert day1_res["transition_occurred"] is False  # No previous regime recorded

    # Verify Day 1 DB insertion
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_lttd WHERE data_as_of = '2026-06-01'")
        row = cursor.fetchone()
        assert row is not None
        assert row["regime"] == "BULL"
        assert row["final_score"] == 0.8
        assert row["target_exposure"] == 0.8
        assert row["posterior_prob"] == 0.9

        # No transitions yet
        cursor.execute("SELECT COUNT(*) FROM regime_transitions")
        assert cursor.fetchone()[0] == 0

    # Day 2: Same regime (BULL), score changes
    day2_res = engine.run(
        date_str="2026-06-02",
        final_score=0.4,
        regime="BULL",
        posteriors={"BULL": 0.8, "BEAR": 0.05, "SIDEWAYS": 0.15},
        log_return=0.005,
        realized_volatility=0.11,
        db_path=db_path
    )
    assert day2_res["status"] == "success"
    assert day2_res["target_exposure"] == 0.4
    assert day2_res["transition_occurred"] is False  # Same regime

    # Verify Day 2 DB insertion
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_lttd WHERE data_as_of = '2026-06-02'")
        row = cursor.fetchone()
        assert row is not None
        assert row["regime"] == "BULL"
        assert row["final_score"] == 0.4
        assert row["target_exposure"] == 0.4
        assert row["posterior_prob"] == 0.8

        # Still no transitions
        cursor.execute("SELECT COUNT(*) FROM regime_transitions")
        assert cursor.fetchone()[0] == 0

    # Day 3: Shift to SIDEWAYS regime, score capped
    day3_res = engine.run(
        date_str="2026-06-03",
        final_score=0.7,
        regime="SIDEWAYS",
        posteriors={"BULL": 0.2, "BEAR": 0.1, "SIDEWAYS": 0.7},
        log_return=-0.015,
        realized_volatility=0.18,
        db_path=db_path
    )
    assert day3_res["status"] == "success"
    assert day3_res["target_exposure"] == 0.5  # Capped at 0.5 in SIDEWAYS
    assert day3_res["transition_occurred"] is True  # Transition from BULL to SIDEWAYS

    # Verify Day 3 DB insertion and Transition insertion
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_lttd WHERE data_as_of = '2026-06-03'")
        row = cursor.fetchone()
        assert row is not None
        assert row["regime"] == "SIDEWAYS"
        assert row["final_score"] == 0.7
        assert row["target_exposure"] == 0.5
        assert row["posterior_prob"] == 0.7

        # Transition recorded
        cursor.execute("SELECT * FROM regime_transitions WHERE transition_date = '2026-06-03'")
        transition = cursor.fetchone()
        assert transition is not None
        assert transition["previous_regime"] == "BULL"
        assert transition["new_regime"] == "SIDEWAYS"
        assert transition["posterior_probability"] == 0.7
        
        metrics = json.loads(transition["triggering_metrics"])
        assert metrics["Log Return"] == -0.015
        assert metrics["Realized Volatility"] == 0.18
