import pytest
import sqlite3
from src.execution.db import init_db, get_connection


@pytest.fixture
def db_conn(tmp_path):
    db_path = str(tmp_path / "test_schema.db")
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def test_daily_lttd_constraints(db_conn):
    cursor = db_conn.cursor()

    # Valid insert
    cursor.execute(
        "INSERT INTO daily_lttd (date, regime, final_score) VALUES ('2023-01-01', 'BULL', 0.8)"
    )
    db_conn.commit()

    # Invalid regime
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO daily_lttd (date, regime, final_score) VALUES ('2023-01-02', 'INVALID', 0.8)"
        )

    # Invalid final_score (too high)
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO daily_lttd (date, regime, final_score) VALUES ('2023-01-03', 'BEAR', 1.5)"
        )

    # Invalid final_score (too low)
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO daily_lttd (date, regime, final_score) VALUES ('2023-01-04', 'BEAR', -1.5)"
        )


def test_indicator_scores_constraints(db_conn):
    cursor = db_conn.cursor()

    # Valid insert
    cursor.execute(
        "INSERT INTO indicator_scores (date, indicator_name, score) VALUES ('2023-01-01', 'rsi', 1)"
    )
    db_conn.commit()

    # Invalid score
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO indicator_scores (date, indicator_name, score) VALUES ('2023-01-02', 'rsi', 0)"
        )


def test_regime_transitions_constraints(db_conn):
    cursor = db_conn.cursor()

    # Valid insert
    cursor.execute(
        """INSERT INTO regime_transitions (transition_date, previous_regime, new_regime, posterior_probability, triggering_metrics) VALUES ('2023-01-01', 'BEAR', 'BULL', 0.9, '{"mvrv": 2.0}')"""
    )
    db_conn.commit()

    # Invalid previous regime
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO regime_transitions (transition_date, previous_regime, new_regime, posterior_probability) VALUES ('2023-01-02', 'UNKNOWN', 'BULL', 0.9)"
        )
