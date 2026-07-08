import sqlite3
import os
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "database/lttd.db")


@contextmanager
def get_connection(db_path=DEFAULT_DB_PATH, timeout=10.0):
    import sys
    if "/home/ubuntu/projects" not in sys.path:
        sys.path.insert(0, "/home/ubuntu/projects")
    from db_connector import get_wal_connection
    conn = get_wal_connection(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    try:
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
                final_score REAL CHECK(final_score >= -1.0 AND final_score <= 1.0) NOT NULL,
                target_exposure REAL CHECK(target_exposure >= 0.0 AND target_exposure <= 2.5) NOT NULL,
                posterior_prob REAL,
                circuit_breaker_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alter table to add circuit_breaker_active if it doesn't exist
        try:
            cursor.execute("ALTER TABLE daily_lttd ADD COLUMN circuit_breaker_active BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column probably already exists

        # Check if existing indicator_scores table has the check constraint
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='indicator_scores'")
        row = cursor.fetchone()
        if row and "CHECK" in row[0] and "score >= -1.0" in row[0]:
            # Migrate table to remove CHECK constraint (allows values like Shannon Entropy)
            cursor.execute("ALTER TABLE indicator_scores RENAME TO indicator_scores_old")
            cursor.execute("""
                CREATE TABLE indicator_scores (
                    date TEXT,
                    indicator_name TEXT,
                    score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, indicator_name)
                )
            """)
            cursor.execute("""
                INSERT INTO indicator_scores (date, indicator_name, score, created_at)
                SELECT date, indicator_name, score, created_at FROM indicator_scores_old
            """)
            cursor.execute("DROP TABLE indicator_scores_old")

        # Create indicator_scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicator_scores (
                date TEXT,
                indicator_name TEXT,
                score REAL NOT NULL,
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
