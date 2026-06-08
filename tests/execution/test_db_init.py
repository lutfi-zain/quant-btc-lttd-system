import os
import sqlite3
import pytest
from src.execution.db import init_db, get_connection

def test_init_db_creates_file_and_wal_mode(tmp_path):
    db_path = str(tmp_path / "test_init.db")
    init_db(db_path)
    
    assert os.path.exists(db_path)
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL"
