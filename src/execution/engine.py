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

    def get_previous_exposure_from_db(self, date_str: str, db_path=None) -> Optional[float]:
        """
        Queries the database to find the last recorded target_exposure prior to the current date.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT target_exposure FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 1",
                    (date_str,),
                )
                row = cursor.fetchone()
                if row:
                    return row["target_exposure"]
        except Exception as e:
            logger.warning(f"Could not fetch previous target_exposure from DB: {e}")
            
    def get_previous_circuit_breaker_from_db(self, date_str: str, db_path=None) -> bool:
        """
        Queries the database to find the last recorded circuit_breaker_active prior to the current date.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT circuit_breaker_active FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 1",
                    (date_str,),
                )
                row = cursor.fetchone()
                if row and "circuit_breaker_active" in row.keys():
                    return bool(row["circuit_breaker_active"])
        except Exception as e:
            logger.warning(f"Could not fetch previous circuit_breaker_active from DB: {e}")
            
        return False

    def get_days_since_exit_from_db(self, date_str: str, db_path=None) -> int:
        """
        Calculates the number of consecutive days the exposure has been < 0.9 prior to date_str.
        If the last exposure was >= 0.9, returns 0.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT target_exposure FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 100",
                    (date_str,),
                )
                rows = cursor.fetchall()
                if not rows:
                    return 999  # Safe default if no history
                
                count = 0
                for row in rows:
                    if row["target_exposure"] >= 0.9:
                        break
                    count += 1
                return count
        except Exception as e:
            logger.warning(f"Could not calculate days_since_exit from DB: {e}")
            return 999

    def get_days_in_position_from_db(self, date_str: str, db_path=None) -> int:
        """
        Calculates the number of consecutive days the exposure has been >= 0.9 prior to date_str.
        If the last exposure was < 0.9, returns 0.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT target_exposure FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 100",
                    (date_str,),
                )
                rows = cursor.fetchall()
                if not rows:
                    return 0  # Safe default if no history
                
                count = 0
                for row in rows:
                    if row["target_exposure"] < 0.9:
                        break
                    count += 1
                return count
        except Exception as e:
            logger.warning(f"Could not calculate days_in_position from DB: {e}")
            return 0

    def get_previous_scores_from_db(self, date_str: str, db_path=None) -> list:
        """
        Queries the database to find recent raw final_scores prior to the current date.
        """
        from src.execution.database import get_connection
        
        db_args = {}
        if db_path is not None:
            db_args["db_path"] = db_path

        try:
            with get_connection(**db_args) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT final_score FROM daily_lttd WHERE date < ? ORDER BY date DESC LIMIT 100",
                    (date_str,),
                )
                rows = cursor.fetchall()
                # Rows are ordered descending (newest first). Reverse to make chronological.
                return [row["final_score"] for row in reversed(rows)]
        except Exception as e:
            logger.warning(f"Could not fetch previous scores from DB: {e}")
            
        return []

    def run(
        self,
        date_str: str,
        final_score: float,
        regime: str,
        posteriors: Optional[Dict[str, float]] = None,
        log_return: float = 0.0,
        realized_volatility: float = 0.0,
        composite_value: Optional[float] = None,
        db_path=None,
        price: Optional[float] = None,
        ma_val: Optional[float] = None,
        entropy_val: Optional[float] = None,
        er_val: Optional[float] = None,
        cloud_min: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Coordinated Layer 5 pipeline run.
        Computes target exposure, logs regime transitions, and persists state to SQLite.
        """
        from src.execution.sizing import (
            calculate_target_exposure,
            super_smoother,
            SUPERSMOOTHER_PERIOD_ENTRY,
            SUPERSMOOTHER_PERIOD_EXIT,
        )
        from src.execution.logger import RegimeTransitionLogger
        from src.execution.persistence import upsert_daily_lttd, log_regime_transition
        import json
        import pandas as pd

        # Use exact regime case
        regime_upper = regime

        # Retrieve previous exposure, circuit breaker, days_since_exit, and days_in_position states
        prev_exposure = self.get_previous_exposure_from_db(date_str, db_path=db_path)
        prev_cb = self.get_previous_circuit_breaker_from_db(date_str, db_path=db_path)
        days_since_exit = self.get_days_since_exit_from_db(date_str, db_path=db_path)
        days_in_position = self.get_days_in_position_from_db(date_str, db_path=db_path)

        # Compute SuperSmoother smoothed scores for entry and exit using asymmetric periods
        past_scores = self.get_previous_scores_from_db(date_str, db_path=db_path)
        all_scores = past_scores + [final_score]
        scores_series = pd.Series(all_scores)
        
        smoothed_entry = float(super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_ENTRY).iloc[-1])
        smoothed_exit = float(super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_EXIT).iloc[-1])

        # 1. Calculate target exposure using the smoothed scores
        target_exposure, circuit_breaker_active = calculate_target_exposure(
            smoothed_entry,
            smoothed_exit,
            realized_volatility,
            regime_upper,
            prev_exposure=prev_exposure,
            composite_value=composite_value,
            prev_circuit_breaker_active=prev_cb,
            days_since_exit=days_since_exit,
            days_in_position=days_in_position,
            price=price,
            ma_val=ma_val,
            entropy_val=entropy_val,
            er_val=er_val,
            cloud_min=cloud_min
        )

        # 2. Extract posteriors
        posteriors_clean = posteriors or {"BULL": 0.0, "BEAR": 0.0, "SIDEWAYS": 0.0}
        p_bull = posteriors_clean.get("BULL", 0.0)
        p_bear = posteriors_clean.get("BEAR", 0.0)
        p_sideways = posteriors_clean.get("SIDEWAYS", 0.0)
        active_posterior = max(posteriors_clean.values()) if posteriors_clean else 0.0

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
            circuit_breaker_active=circuit_breaker_active,
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
            "circuit_breaker_active": circuit_breaker_active,
            "transition_occurred": transition_payload is not None,
        }
