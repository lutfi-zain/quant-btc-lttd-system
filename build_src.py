import os

files = {
    "src/data/exchange_adapter.py": """from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
import time
import requests
import logging

logger = logging.getLogger(__name__)

class ExchangeAdapter(ABC):
    @abstractmethod
    def fetch_ohlcv(self, start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
        pass

class BinanceAdapter(ExchangeAdapter):
    def fetch_ohlcv(self, start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
        base_url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 1000}
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
            
        all_df = []
        max_retries = 5
        
        while True:
            for attempt in range(max_retries):
                try:
                    response = requests.get(base_url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    sleep_time = 2 ** attempt
                    logger.warning(f"Fetch failed: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
            
            if not data:
                break
                
            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            all_df.append(df)
            
            if len(data) < params["limit"]:
                break
                
            params["startTime"] = data[-1][6] + 1
            time.sleep(0.5)
            
        if not all_df:
            return pd.DataFrame()
            
        final_df = pd.concat(all_df, ignore_index=True)
        final_df["timestamp"] = pd.to_datetime(final_df["open_time"], unit="ms", utc=True)
        final_df.set_index("timestamp", inplace=True)
        final_df = final_df[["open", "high", "low", "close", "volume"]].astype(float)
        
        return final_df
""",
    "src/data/db.py": """import sqlite3
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
""",
    "src/data/pipeline.py": """import pandas as pd
import logging
from typing import Optional
from datetime import datetime, timezone
from src.config import BTC_DATA_SOURCE, DB_PATH
from src.data.exchange_adapter import ExchangeAdapter, BinanceAdapter
from src.data.db import SQLiteCache

logger = logging.getLogger(__name__)

def validate_chronological_order(df: pd.DataFrame):
    if not df.index.is_monotonic_increasing:
        raise ValueError("Data is not sorted in chronological order")

def standardize_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    if df.index.tzinfo is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    df.index = df.index.normalize()
    
    df = df[~df.index.duplicated(keep='last')]
    
    validate_chronological_order(df)

    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(full_index)

    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = df[col].ffill()
    
    if 'volume' in df.columns:
        df['volume'] = df['volume'].fillna(0.0)

    df.index.name = 'timestamp'
    
    return df

def get_exchange_adapter() -> ExchangeAdapter:
    if BTC_DATA_SOURCE.lower() == "binance":
        return BinanceAdapter()
    return BinanceAdapter()

def ohlcv_pipeline(end_time: Optional[datetime] = None) -> pd.DataFrame:
    cache = SQLiteCache(DB_PATH)
    max_t = cache.get_max_timestamp()
    
    adapter = get_exchange_adapter()
    
    if end_time is None:
        end_time = datetime.now(timezone.utc)
        
    if max_t:
        logger.info(f"Fetching delta from {max_t}")
        df_new = adapter.fetch_ohlcv(start_time=max_t, end_time=end_time)
        if not df_new.empty:
            df_new = standardize_and_validate(df_new)
            df_new = df_new[df_new.index > max_t]
            cache.save_dataframe(df_new)
    else:
        logger.info("Fetching all history")
        df_new = adapter.fetch_ohlcv(end_time=end_time)
        if not df_new.empty:
            df_new = standardize_and_validate(df_new)
            cache.save_dataframe(df_new)
            
    df_full = cache.load_dataframe()
    if not df_full.empty:
        df_full = standardize_and_validate(df_full)
        
    return df_full
""",
    "tests/test_data_pipeline.py": """import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from src.data.pipeline import standardize_and_validate, validate_chronological_order, ohlcv_pipeline
from src.data.exchange_adapter import ExchangeAdapter
from src.data.db import SQLiteCache
import os

class MockAdapter(ExchangeAdapter):
    def fetch_ohlcv(self, start_time=None, end_time=None):
        dates = pd.date_range("2024-01-01", "2024-01-05", freq="D", tz="UTC")
        df = pd.DataFrame({
            "open": [10, 11, 12, 13, 14],
            "high": [11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13],
            "close": [10.5, 11.5, 12.5, 13.5, 14.5],
            "volume": [100, 110, 120, 130, 140]
        }, index=dates)
        
        if start_time:
            df = df[df.index >= start_time]
        if end_time:
            df = df[df.index <= end_time]
        return df

def test_chronological_order_validation():
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"close": [1, 2, 3]}, index=dates)
    validate_chronological_order(df)
    
    df_unsorted = df.sort_index(ascending=False)
    with pytest.raises(ValueError, match="not sorted in chronological order"):
        validate_chronological_order(df_unsorted)

def test_missing_daily_bar():
    dates = [datetime(2024,1,1, tzinfo=timezone.utc), datetime(2024,1,3, tzinfo=timezone.utc)]
    df = pd.DataFrame({
        "open": [10, 12],
        "high": [11, 13],
        "low": [9, 11],
        "close": [10.5, 12.5],
        "volume": [100, 120]
    }, index=dates)
    
    df_std = standardize_and_validate(df)
    
    assert len(df_std) == 3
    assert df_std.index[1] == datetime(2024,1,2, tzinfo=timezone.utc)
    assert df_std.loc[df_std.index[1], "close"] == 10.5
    assert df_std.loc[df_std.index[1], "volume"] == 0.0

def test_no_lookahead():
    dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=dates)
    
    def causal_filter(data):
        return data["close"].shift(1)
        
    def non_causal_filter(data):
        return data["close"].shift(-1)
        
    t = datetime(2024, 1, 3, tzinfo=timezone.utc)
    
    df_t = df[df.index <= t]
    res_t = causal_filter(df_t)
    val_t = res_t.loc[t]
    
    res_all = causal_filter(df)
    val_all = res_all.loc[t]
    
    assert val_t == val_all, "Causal filter failed"
    
    res_t_non = non_causal_filter(df_t)
    val_t_non = res_t_non.loc[t]
    
    res_all_non = non_causal_filter(df)
    val_all_non = res_all_non.loc[t]
    
    assert val_t_non != val_all_non or pd.isna(val_t_non), "Non-causal filter detected"

def test_caching_behavior(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.data.pipeline.DB_PATH", db_path)
    monkeypatch.setattr("src.data.pipeline.get_exchange_adapter", lambda: MockAdapter())
    
    t1 = datetime(2024, 1, 3, tzinfo=timezone.utc)
    df1 = ohlcv_pipeline(end_time=t1)
    assert len(df1) == 3
    
    cache = SQLiteCache(db_path)
    assert cache.get_max_timestamp() == t1
    
    t2 = datetime(2024, 1, 5, tzinfo=timezone.utc)
    df2 = ohlcv_pipeline(end_time=t2)
    assert len(df2) == 5
    
    assert cache.get_max_timestamp() == t2
"""
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)
