import pandas as pd
from src.data.brk_fetcher import BRKDataFetcher
from src.features.ou_calibration import estimate_ou_halflife


class WFOEnsemble:
    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()
        self.ou_halflives = {}

    def fetch_deep_matrices(self, start=-1000):
        series_list = ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
        return self.fetcher.fetch_historical_bulk(series_list, start=start)

    def recalibrate_ou_halflife(
        self,
        log_returns: pd.Series,
        train_end: pd.Timestamp,
        train_window_days: int = 1095,
    ) -> float:
        """
        Recalibrate the OU Half-Life strictly using purged in-sample data.
        In-sample data starts at (train_end - train_window_days) and ends at train_end.
        """
        train_start = train_end - pd.Timedelta(days=train_window_days)
        in_sample = log_returns.loc[train_start:train_end]

        # Recalibrate
        hl = estimate_ou_halflife(in_sample, min_bars=250)
        return hl

    def run_wfo_calibration(
        self,
        log_returns: pd.Series,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        legacy_fixed_window: bool = False,
    ) -> pd.Series:
        """
        Runs quarterly recalibration of OU half-life over the dataset.
        If legacy_fixed_window is True, forces a static 200-day window.
        """
        target_index = log_returns.loc[start_date:end_date].index
        if legacy_fixed_window:
            return pd.Series(200.0, index=target_index)

        # Generate quarterly dates
        quarterly_dates = pd.date_range(start=start_date, end=end_date, freq="QS")

        # Calculate half-life for each quarter using in-sample (past 3-year) data
        for q_date in quarterly_dates:
            # Training data ends exactly before the quarter starts
            train_end = q_date - pd.Timedelta(days=1)
            hl = self.recalibrate_ou_halflife(log_returns, train_end)
            self.ou_halflives[q_date] = hl

        # Create a series mapped to daily index
        daily_hl = pd.Series(350.0, index=target_index)

        for i, date in enumerate(daily_hl.index):
            prev_quarters = [q for q in quarterly_dates if q <= date]
            if prev_quarters:
                prev_q = max(prev_quarters)
                daily_hl.iloc[i] = self.ou_halflives[prev_q]
            else:
                daily_hl.iloc[i] = 350.0

        return daily_hl
