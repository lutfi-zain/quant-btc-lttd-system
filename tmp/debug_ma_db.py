#!/usr/bin/env python3
import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.data.db import SQLiteCache
from src.backtest.wfo import point_in_time_join
from src.execution.sizing import MA_PERIOD

def main():
    conn = sqlite3.connect("database/lttd.db")
    df_ohlcv = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
    conn.close()
    
    # Reconstruct df_ohlcv timezone aware index just like backfill_all.py
    df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
    df_ohlcv.set_index("timestamp", inplace=True)
    
    # Mock df_onchain with stamp column to merge
    df_onchain = pd.DataFrame(index=df_ohlcv.index)
    df_onchain["stamp"] = df_ohlcv.index
    df_onchain["sth_mvrv"] = 1.0
    
    df_merged = point_in_time_join(df_ohlcv, df_onchain)
    ma_series = df_merged["close"].rolling(MA_PERIOD).mean()
    
    t_date = pd.Timestamp("2018-05-10", tz="UTC")
    print(f"t_date: {t_date} | type: {type(t_date)}")
    print(f"Index type: {type(df_merged.index)}")
    print(f"Is t_date in index: {t_date in df_merged.index}")
    
    if t_date in df_merged.index:
        close_price = df_merged.loc[t_date, "close"]
        ma_val = ma_series.loc[t_date]
        print(f"close_price: {close_price} | type: {type(close_price)}")
        print(f"ma_val: {ma_val} | type: {type(ma_val)} | isna: {pd.isna(ma_val)}")

if __name__ == "__main__":
    main()
