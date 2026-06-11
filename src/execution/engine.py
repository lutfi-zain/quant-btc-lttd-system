import logging
from typing import Optional, Dict, Any
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

    def get_previous_regime_from_db(self, date_str: str, db_path=None) -> Optional[str]:
        """
        Queries the database to find the last recorded regime prior to the current date.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT regime FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 1",
                    (date_str,),
                )
                row = cursor.fetchone()
                if row:
                    return row["regime"]
        except Exception as e:
            logger.warning(f"Could not fetch previous regime from DB: {e}")
            
        return None

    def run(
        self,
        date_str: str,
        final_score: float,
        regime: str,
        posteriors: Optional[Dict[str, float]] = None,
        log_return: float = 0.0,
        realized_volatility: float = 0.0,
        db_path=None,
    ) -> Dict[str, Any]:
        """
        Coordinated Layer 5 pipeline run.
        Computes target exposure, logs regime transitions, and persists state to SQLite.
        """
        from src.execution.sizing import calculate_target_exposure
        from src.execution.logger import RegimeTransitionLogger
        from src.execution.persistence import upsert_daily_lttd, log_regime_transition
        import json

        # Normalize regime
        regime_upper = regime.upper()

        # 1. Calculate target exposure
        target_exposure = calculate_target_exposure(final_score, regime_upper)

        # 2. Extract posteriors
        posteriors_clean = posteriors or {"BULL": 0.0, "BEAR": 0.0, "SIDEWAYS": 0.0}
        p_bull = posteriors_clean.get("BULL", 0.0)
        p_bear = posteriors_clean.get("BEAR", 0.0)
        p_sideways = posteriors_clean.get("SIDEWAYS", 0.0)
        active_posterior = posteriors_clean.get(regime_upper, 0.0)

        # 3. Retrieve previous regime from database
        previous_regime = self.get_previous_regime_from_db(date_str, db_path=db_path)

        # 4. Check and log regime transitions
        transition_logger = RegimeTransitionLogger(previous_regime=previous_regime)
        transition_payload = transition_logger.check_and_log(
            current_regime=regime_upper,
            brk_stamp=date_str,
            p_bull=p_bull,
            p_bear=p_bear,
            p_sideways=p_sideways,
            log_return=log_return,
            realized_volatility=realized_volatility,
        )

        # 5. Persist the final daily record to the daily_lttd table
        persist_kwargs = {}
        if db_path is not None:
            persist_kwargs["db_path"] = db_path

        upsert_daily_lttd(
            date=date_str,
            regime=regime_upper,
            final_score=final_score,
            target_exposure=target_exposure,
            posterior_prob=active_posterior,
            **persist_kwargs,
        )

        # 6. If a transition occurred, write to regime_transitions table
        if transition_payload is not None:
            triggering_metrics_str = json.dumps({
                "Log Return": log_return,
                "Realized Volatility": realized_volatility,
            })
            log_regime_transition(
                transition_date=date_str,
                previous_regime=previous_regime,
                new_regime=regime_upper,
                posterior_probability=active_posterior,
                triggering_metrics=triggering_metrics_str,
                **persist_kwargs,
            )

        return {
            "status": "success",
            "date": date_str,
            "regime": regime_upper,
            "final_score": final_score,
            "target_exposure": target_exposure,
            "transition_occurred": transition_payload is not None,
        }
