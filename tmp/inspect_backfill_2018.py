#!/usr/bin/env python3
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from brk_client import BrkClient
from src.data.exchange_adapter import BinanceAdapter
from src.data.db import SQLiteCache
from src.data.brk_ingestion_service import BRKIngestionService
from src.backtest.wfo import point_in_time_join

def main():
    print("Fetching data from API...")
    res_price = requests.get('https://bitview.space/api/series/bulk?series=price_ohlc&index=day1&start=-4500').json()
    brk_client = BrkClient()
    start_date = brk_client.index_to_date("day1", res_price["start"])
    dates = pd.date_range(start=start_date, periods=len(res_price["data"]), freq="D", tz="UTC", name="timestamp")
    df_ohlcv = pd.DataFrame(res_price["data"], index=dates, columns=["open", "high", "low", "close"])
    df_ohlcv["volume"] = 1.0
    
    # Fetch bulk on-chain history
    ingestion = BRKIngestionService()
    df_onchain = ingestion.fetch_historical(lookback_days=4500)
    
    # Merge datasets causally
    df_merged = point_in_time_join(df_ohlcv, df_onchain)
    
    ma_series = df_merged["close"].rolling(229).mean()
    
    t_date = pd.Timestamp("2018-05-10", tz="UTC")
    print("\n--- RESULTS ON 2018-05-10 in df_merged ---")
    print(f"Index exists: {t_date in df_merged.index}")
    if t_date in df_merged.index:
        close_price = df_merged.loc[t_date, "close"]
        ma_val = ma_series.loc[t_date]
        print(f"Close price: {close_price}")
        print(f"MA (229)   : {ma_val}")
        print(f"Price > MA : {close_price > ma_val}")

if __name__ == "__main__":
    main()
