import pandas as pd
from datetime import datetime, timedelta, timezone
from src.data.brk_fetcher import BRKDataFetcher, StaleOnChainDataError


class OnChainFeed:
    """
    OnChainFeed layer for fetching and validating daily Bitcoin On-Chain metrics.
    Enforces strict causality (stamps <= current bar time) and staleness thresholds.
    """

    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()
        self.series_list = [
            "sth_mvrv",
            "sth_nupl",
            "sth_sopr_24h",
            "sth_supply_in_profit",
        ]

    def fetch_historical_bulk(self, start: int = None) -> pd.DataFrame:
        """
        Fetches historical bulk on-chain data and returns it aligned in a DataFrame.
        """
        res = self.fetcher.fetch_historical_bulk(self.series_list, start=start)

        if not isinstance(res, list):
            res = [res]

        df_dict = {}
        for i, name in enumerate(self.series_list):
            s_data = res[i]
            start_idx = s_data["start"]
            # Map index to date
            start_date = self.fetcher.client.index_to_date("day1", start_idx)
            dates = pd.date_range(
                start=start_date, periods=len(s_data["data"]), freq="D"
            )
            df_dict[name] = pd.Series(s_data["data"], index=dates)

        return pd.DataFrame(df_dict)

    def fetch_latest_causal(self, current_bar_time: datetime) -> dict:
        """
        Fetches the latest values for the on-chain metrics, ensuring they are causal
        relative to current_bar_time.
        If any metric is stale (older than 3 days), defaults to 0.0 (neutral signal weight).
        """
        signals = {}
        # Ensure current_bar_time has timezone info (UTC)
        if current_bar_time.tzinfo is None:
            current_bar_time = current_bar_time.replace(tzinfo=timezone.utc)

        for name in self.series_list:
            try:
                res = self.fetcher.fetch_latest(name)
                val = res["value"]
                stamp = res["stamp"]

                # Ensure stamp is timezone-aware
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)

                # Strict causal stamp validation
                if stamp > current_bar_time:
                    raise StaleOnChainDataError(
                        f"Lookahead detected: stamp {stamp} > current bar time {current_bar_time}"
                    )

                # Staleness threshold check (max 3 days)
                if current_bar_time - stamp > timedelta(days=3):
                    # Stale data: fallback to neutral 0.0
                    signals[name] = 0.0
                else:
                    signals[name] = val

            except StaleOnChainDataError:
                # Apply 0.0 neutral weight
                signals[name] = 0.0

        return signals


class OnChainSignalEngine:
    """
    Backward-compatible wrapper for realtime on-chain signal retrieval.
    """

    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()
        self.feed = OnChainFeed(self.fetcher)

    def get_realtime_signals(self):
        signals = {}
        for series in self.feed.series_list:
            signals[series] = self.fetcher.fetch_latest(series)["value"]
        return signals
