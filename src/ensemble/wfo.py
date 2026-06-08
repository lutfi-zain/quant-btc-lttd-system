from src.data.brk_fetcher import BRKDataFetcher


class WFOEnsemble:
    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()

    def fetch_deep_matrices(self, start=-1000):
        series_list = ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
        return self.fetcher.fetch_historical_bulk(series_list, start=start)
