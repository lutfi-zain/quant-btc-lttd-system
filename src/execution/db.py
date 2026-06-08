import sqlite3
import os
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "database/lttd.db")

@contextmanager
def get_connection(db_path=DEFAULT_DB_PATH):
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path=DEFAULT_DB_PATH):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_lttd (
                date TEXT PRIMARY KEY,
                regime TEXT CHECK(regime IN ('BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
                final_score REAL CHECK(final_score >= -1.0 AND final_score <= 1.0) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicator_scores (
                date TEXT,
                indicator_name TEXT,
                score INTEGER CHECK(score IN (-1, 1)) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, indicator_name)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regime_transitions (
                transition_date TEXT PRIMARY KEY,
                previous_regime TEXT CHECK(previous_regime IN ('BULL', 'BEAR', 'SIDEWAYS')),
                new_regime TEXT CHECK(new_regime IN ('BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
                posterior_probability REAL,
                triggering_metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
