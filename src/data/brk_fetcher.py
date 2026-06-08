import pandas as pd
from datetime import datetime, timedelta, timezone
from brk_client import BrkClient


class StaleOnChainDataError(Exception):
    pass


class BRKDataFetcher:
    def __init__(self, base_url="https://bitview.space"):
        self.client = BrkClient(base_url=base_url)

    def fetch_latest(self, series_name: str) -> dict:
        """
        Fetch the latest value for a given BRK series.
        Asserts that the data is fresh (stamp >= current_date - 1 day).
        """
        # The /latest endpoint in BRK API returns just the float value.
        # To get the timestamp of the latest data, we check the sync status.
        value = self.client.get_series_latest(series_name, "day1")
        status = self.client.get_sync_status()
        stamp_str = status.get("last_indexed_at")

        stamp = datetime.strptime(stamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        current_date = datetime.now(timezone.utc)

        if stamp < current_date - timedelta(days=1):
            raise StaleOnChainDataError(
                f"Data is stale! stamp: {stamp_str}, current_date: {current_date.isoformat()}"
            )

        return {"value": value, "stamp": stamp}

    def fetch_historical_bulk(self, series_list: list, start: int = None) -> list:
        """
        Fetch multiple series in bulk for WFO and historical training.
        start can be negative (e.g. -365) to fetch last N days, or an exact index.
        """
        # In BrkClient, start is passed to the bulk endpoint.
        kwargs = {}
        if start is not None:
            kwargs["start"] = start

        return self.client.get_series_bulk(series_list, index="day1", **kwargs)

    def align_with_ohlcv(
        self, brk_df: pd.DataFrame, ohlcv_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Join on-chain data with OHLCV using the stamp index and apply ffill(limit=1).
        """
        # Ensure indices are datetime objects for joining
        if not isinstance(brk_df.index, pd.DatetimeIndex):
            brk_df.index = pd.to_datetime(brk_df.index)
        if not isinstance(ohlcv_df.index, pd.DatetimeIndex):
            ohlcv_df.index = pd.to_datetime(ohlcv_df.index)

        # Join dataframes on index
        merged_df = ohlcv_df.join(brk_df, how="left")

        # Forward fill up to 1 day for on-chain data
        # Only ffill the columns that came from brk_df
        brk_cols = brk_df.columns
        merged_df[brk_cols] = merged_df[brk_cols].ffill(limit=1)

        return merged_df
