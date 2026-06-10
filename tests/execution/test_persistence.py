import pytest
from src.execution.db import init_db, get_connection
from src.execution.persistence import (
    upsert_daily_lttd,
    upsert_indicator_scores,
    log_regime_transition,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_persistence.db")
    init_db(path)
    return path


def test_upsert_daily_lttd(db_path):
    # Initial insert
    upsert_daily_lttd("2023-01-01", "BULL", 0.5, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_lttd WHERE date = '2023-01-01'")
        row = cursor.fetchone()
        assert row["regime"] == "BULL"
        assert row["final_score"] == 0.5

    # Update (idempotent)
    upsert_daily_lttd("2023-01-01", "BEAR", -0.8, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_lttd WHERE date = '2023-01-01'")
        row = cursor.fetchone()
        assert row["regime"] == "BEAR"
        assert row["final_score"] == -0.8

        cursor.execute("SELECT COUNT(*) FROM daily_lttd")
        assert cursor.fetchone()[0] == 1


def test_upsert_indicator_scores(db_path):
    scores1 = {"rsi": 1, "macd": -1}
    upsert_indicator_scores("2023-01-01", scores1, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM indicator_scores WHERE date = '2023-01-01' ORDER BY indicator_name"
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0]["indicator_name"] == "macd"
        assert rows[0]["score"] == -1
        assert rows[1]["indicator_name"] == "rsi"
        assert rows[1]["score"] == 1

    # Update one, keep another
    scores2 = {"rsi": -1, "macd": -1}
    upsert_indicator_scores("2023-01-01", scores2, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT score FROM indicator_scores WHERE date = '2023-01-01' AND indicator_name = 'rsi'"
        )
        assert cursor.fetchone()[0] == -1


def test_log_regime_transition(db_path):
    log_regime_transition("2023-01-01", "BULL", "BEAR", 0.95, '{"rsi": 0.2}', db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM regime_transitions WHERE transition_date = '2023-01-01'"
        )
        row = cursor.fetchone()
        assert row["previous_regime"] == "BULL"
        assert row["new_regime"] == "BEAR"
        assert row["triggering_metrics"] == '{"rsi": 0.2}'

    # Update idempotent
    log_regime_transition(
        "2023-01-01", "SIDEWAYS", "BEAR", 0.99, '{"rsi": 0.1}', db_path
    )
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM regime_transitions WHERE transition_date = '2023-01-01'"
        )
        row = cursor.fetchone()
        assert row["previous_regime"] == "SIDEWAYS"
        assert row["posterior_probability"] == 0.99
        assert row["triggering_metrics"] == '{"rsi": 0.1}'


def test_upsert_pca_components(db_path):
    from src.execution.persistence import upsert_pca_components

    components1 = {"PC1": 0.25, "PC2": -0.85}
    upsert_pca_components("2023-01-01", components1, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pca_components WHERE date = '2023-01-01' ORDER BY component_name"
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0]["component_name"] == "PC1"
        assert rows[0]["value"] == 0.25
        assert rows[1]["component_name"] == "PC2"
        assert rows[1]["value"] == -0.85

    # Update idempotent
    components2 = {"PC1": 0.50}
    upsert_pca_components("2023-01-01", components2, db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM pca_components WHERE date = '2023-01-01' AND component_name = 'PC1'"
        )
        assert cursor.fetchone()[0] == 0.50

