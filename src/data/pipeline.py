import pandas as pd
import logging
from typing import Optional
from datetime import datetime, timezone
from src.config import BTC_DATA_SOURCE, DB_PATH
from src.data.exchange_adapter import ExchangeAdapter, BinanceAdapter, BRKExchangeAdapter
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

    df = df[~df.index.duplicated(keep="last")]

    validate_chronological_order(df)

    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
    df = df.reindex(full_index)

    missing_mask = df["close"].isna()
    if "close" in df.columns:
        df["close"] = df["close"].ffill()

    for col in ["open", "high", "low"]:
        if col in df.columns:
            df.loc[missing_mask, col] = df["close"]
            df[col] = df[col].ffill()

    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0.0)

    df.index.name = "timestamp"

    return df


def get_exchange_adapter() -> ExchangeAdapter:
    if BTC_DATA_SOURCE.lower() == "binance":
        return BinanceAdapter()
    return BRKExchangeAdapter()


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
        logger.info("Fetching all history since 2011")
        df_new = adapter.fetch_ohlcv(start_time=datetime(2011, 1, 1, tzinfo=timezone.utc), end_time=end_time)
        if not df_new.empty:
            df_new = standardize_and_validate(df_new)
            cache.save_dataframe(df_new)

    df_full = cache.load_dataframe()
    if not df_full.empty:
        df_full = standardize_and_validate(df_full)

    return df_full
