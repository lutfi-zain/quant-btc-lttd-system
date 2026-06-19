import pandas as pd
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from brk_client import BrkClient


class DataStaleException(Exception):
    """Raised when the latest on-chain data timestamp (stamp) is stale."""
    pass


@dataclass
class BRKFeed:
    """Typed on-chain metrics feed container."""
    sth_mvrv: float
    sth_nupl: float
    sth_sopr_24h: float
    sth_supply_in_profit: float
    stamp: datetime


class BRKIngestionService:
    """
    Ingestion service utilizing brk-client to retrieve daily on-chain metrics
    with lookback constraints and freshness validation.
    """
    def __init__(self, base_url: str = "https://bitview.space"):
        self.client = BrkClient(base_url=base_url)
        self.series_list = [
            "sth_mvrv",
            "sth_nupl",
            "sth_sopr_24h",
            "sth_supply_in_profit",
        ]

    def fetch_latest(self) -> BRKFeed:
        """
        Fetch the latest values for on-chain metrics from the bulk endpoint.
        Uses the sync status last_indexed_at timestamp as the definitive stamp.
        """
        # Fetch the latest daily value for each series
        vals = {}
        for name in self.series_list:
            vals[name] = float(self.client.get_series_latest(name, "day1"))

        # Fetch sync status for stamp
        status = self.client.get_sync_status()
        stamp_str = status.get("last_indexed_at")
        
        # Parse stamp as timezone-aware datetime in UTC
        stamp = datetime.strptime(stamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )

        return BRKFeed(
            sth_mvrv=vals["sth_mvrv"],
            sth_nupl=vals["sth_nupl"],
            sth_sopr_24h=vals["sth_sopr_24h"],
            sth_supply_in_profit=vals["sth_supply_in_profit"],
            stamp=stamp
        )

    def validate_freshness(self, feed: BRKFeed, current_date: datetime) -> None:
        """
        Validates the stamp field from BRK Feed response.
        Asserts that feed.stamp >= current_date - timedelta(days=1).
        If validation fails, raises DataStaleException.
        """
        feed_stamp = feed.stamp
        if feed_stamp.tzinfo is None:
            feed_stamp = feed_stamp.replace(tzinfo=timezone.utc)
            
        ref_date = current_date
        if ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=timezone.utc)
            
        # Strip time if we only compare dates at the daily level
        # Requirement: brk_feed.stamp >= current_date - timedelta(days=1)
        if feed_stamp < ref_date - timedelta(days=1):
            raise DataStaleException(
                f"On-chain data is stale! stamp: {feed_stamp.isoformat()}, "
                f"current_date: {ref_date.isoformat()}"
            )

    def fetch_historical(self, lookback_days: int = 1200) -> pd.DataFrame:
        """
        Fetch historical on-chain metrics in bulk with at least 1,200 days lookback.
        Returns a aligned pandas DataFrame with DatetimeIndex in UTC.
        """
        # Enforce minimum 1,200-day lookback constraint
        lookback = max(lookback_days, 1200)
        query_series = ",".join(self.series_list)
        
        # Fetch bulk
        res = self.client.get_series_bulk(query_series, index="day1", start=-lookback)
        
        if not isinstance(res, list):
            res = [res]
            
        df_dict = {}
        for i, name in enumerate(self.series_list):
            s_data = res[i]
            start_idx = s_data["start"]
            start_date = pd.Timestamp("2009-01-03", tz="UTC") + pd.Timedelta(days=start_idx)
            
            # Map indices to DatetimeIndex
            dates = pd.date_range(
                start=start_date, periods=len(s_data["data"]), freq="D", tz="UTC"
            )
            df_dict[name] = pd.Series(s_data["data"], index=dates)
            
        df = pd.DataFrame(df_dict)
        return df
