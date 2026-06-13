import sqlite3
import os
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "database/lttd.db")


@contextmanager
def get_connection(db_path=DEFAULT_DB_PATH, timeout=10.0):
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)};")
        yield conn
    finally:
        conn.close()


def init_db(db_path=DEFAULT_DB_PATH):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Enable WAL mode explicitly
        cursor.execute("PRAGMA journal_mode=WAL;")

        # Create daily_lttd table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_lttd (
                data_as_of TEXT PRIMARY KEY,
                date TEXT,
                regime TEXT CHECK(regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
                final_score REAL CHECK(final_score >= 0.0 AND final_score <= 1.0) NOT NULL,
                target_exposure REAL CHECK(target_exposure >= 0.0 AND target_exposure <= 1.0) NOT NULL,
                posterior_prob REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indicator_scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicator_scores (
                date TEXT,
                indicator_name TEXT,
                score REAL CHECK(score >= 0.0 AND score <= 1.0) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, indicator_name)
            )
        """)

        # Create pca_components table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pca_components (
                date TEXT,
                component_name TEXT,
                value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, component_name)
            )
        """)

        # Create regime_transitions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regime_transitions (
                transition_date TEXT PRIMARY KEY,
                previous_regime TEXT CHECK(previous_regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')),
                new_regime TEXT CHECK(new_regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
                posterior_probability REAL,
                triggering_metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
