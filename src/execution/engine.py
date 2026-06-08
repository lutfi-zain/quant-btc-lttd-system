import logging
from src.data.brk_fetcher import BRKDataFetcher, StaleOnChainDataError

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()

    def run_daily(self):
        try:
            # retrieve daily LTTD on-chain metrics using fetch_latest
            mvrv = self.fetcher.fetch_latest("sth_mvrv")["value"]
            nupl = self.fetcher.fetch_latest("sth_nupl")["value"]

            # ... process execution logic and write to SQLite ...

            return {"status": "success", "metrics": {"mvrv": mvrv, "nupl": nupl}}
        except StaleOnChainDataError as e:
            # Catch StaleOnChainDataError and safely pause the daily run
            # without writing erroneous zero-values to SQLite
            logger.error(f"Execution paused due to stale on-chain data: {e}")
            return {"status": "paused", "error": str(e)}
