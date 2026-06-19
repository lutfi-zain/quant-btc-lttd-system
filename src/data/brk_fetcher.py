import pandas as pd
import os
import json
from datetime import datetime, timedelta, timezone
from brk_client import BrkClient


class StaleOnChainDataError(Exception):
    pass


class BRKDataFetcher:
    def __init__(self, base_url="https://bitview.space"):
        self.client = BrkClient(base_url=base_url)

    def fetch_latest(self, series_name: str) -> dict:
        res = self.client.get_series(series_name, "day1", start=-1)
        value = res["data"][0]
        last_index = res["end"] - 1
        stamp_date = pd.Timestamp("2009-01-03", tz="UTC") + pd.Timedelta(days=last_index)
        stamp = datetime(
            stamp_date.year, stamp_date.month, stamp_date.day, tzinfo=timezone.utc
        )
        current_date = datetime.now(timezone.utc)
        if stamp < current_date - timedelta(days=1):
            raise StaleOnChainDataError(
                f"Data is stale! stamp: {stamp.isoformat()}, current_date: {current_date.isoformat()}"
            )
        return {"value": value, "stamp": stamp}

    def fetch_historical_bulk(self, query_series, start: int = -1000, **kwargs):
        cache_path = 'brk_cache.json'
        
        if isinstance(query_series, list):
            query_series_str = ",".join(query_series)
        else:
            query_series_str = query_series
            
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                res = json.load(f)
            return res
            
        res = self.client.get_series_bulk(query_series_str, index="day1", **kwargs)
        with open(cache_path, 'w') as f:
            json.dump(res, f)
        return res

    def align_with_ohlcv(
        self, brk_df: pd.DataFrame, ohlcv_df: pd.DataFrame
    ) -> pd.DataFrame:
        if not isinstance(brk_df.index, pd.DatetimeIndex):
            brk_df.index = pd.to_datetime(brk_df.index)
        if not isinstance(ohlcv_df.index, pd.DatetimeIndex):
            ohlcv_df.index = pd.to_datetime(ohlcv_df.index)
        merged_df = ohlcv_df.join(brk_df, how="left")
        brk_cols = brk_df.columns
        merged_df[brk_cols] = merged_df[brk_cols].ffill(limit=1)
        return merged_df
