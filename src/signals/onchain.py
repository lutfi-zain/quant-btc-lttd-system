from src.data.brk_fetcher import BRKDataFetcher


class OnChainSignalEngine:
    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()

    def get_realtime_signals(self):
        # Replaces legacy static array mappings (F1_data to F4_data)
        signals = {}
        for series in ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]:
            signals[series] = self.fetcher.fetch_latest(series)["value"]
        return signals
