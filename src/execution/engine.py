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

    def persist_features(self, date_str: str, indicator_scores: dict, pca_components: dict, db_path=None):
        """
        Persist the raw indicator scores and orthogonalized PCA components into SQLite.
        """
        from src.execution.persistence import upsert_indicator_scores, upsert_pca_components
        
        kwargs = {}
        if db_path is not None:
            kwargs["db_path"] = db_path
            
        upsert_indicator_scores(date_str, indicator_scores, **kwargs)
        upsert_pca_components(date_str, pca_components, **kwargs)
