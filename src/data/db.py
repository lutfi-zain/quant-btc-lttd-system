import sqlite3
import pandas as pd
from contextlib import contextmanager
import os

class SQLiteCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ohlcv (
                    timestamp TEXT PRIMARY KEY,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL
                )
            ''')
            conn.commit()

    def save_dataframe(self, df: pd.DataFrame):
        if df.empty:
            return
        with self.get_connection() as conn:
            df_to_save = df.reset_index()
            df_to_save['timestamp'] = df_to_save['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_to_save.to_sql("ohlcv", conn, if_exists="append", index=False)

    def load_dataframe(self) -> pd.DataFrame:
        with self.get_connection() as conn:
            try:
                df = pd.read_sql("SELECT * FROM ohlcv ORDER BY timestamp ASC", conn)
            except sqlite3.OperationalError:
                return pd.DataFrame()
            if df.empty:
                return df
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.set_index('timestamp', inplace=True)
            return df

    def get_max_timestamp(self):
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(timestamp) FROM ohlcv")
                result = cursor.fetchone()[0]
                if result:
                    return pd.to_datetime(result, utc=True)
            except sqlite3.OperationalError:
                pass
            return None
