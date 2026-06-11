import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import pandas as pd
import numpy as np

from src.data.pipeline import ohlcv_pipeline
from src.data.brk_ingestion_service import BRKIngestionService, BRKFeed, DataStaleException
from src.backtest.wfo import point_in_time_join
from src.regime.hmm import train_hmm, infer_regime
from src.features.builder import FeatureMatrixBuilder
from src.features.ou_calibration import estimate_ou_halflife
from src.features.processor import FeatureProcessor
from src.ensemble.model import L1LassoEnsemble
from src.execution.engine import ExecutionEngine
from src.execution.database import init_db
from src.regime.filter import apply_onchain_overrides

logger = logging.getLogger(__name__)


class LTTDPipeline:
    """
    Central orchestrator for the LTTD Trading System daily sequence.
    Orchestrates:
    - Layer 1: HMM Regime Detection
    - Layer 2: Causal Technical Indicators & On-Chain overrides
    - Layer 3: Feature Processing (VIF pruning & PCA)
    - Layer 4: Ensemble model fitting (L1-Lasso Logistic Regression)
    - Layer 5: Execution Engine Sizing & Persistence (SQLite WAL mode)
    """
    def __init__(self, db_path: Optional[str] = None, base_url: str = "https://bitview.space", ensemble_mode: str = "pca_consensus"):
        self.db_path = db_path
        self.brk_ingestion = BRKIngestionService(base_url=base_url)
        self.execution_engine = ExecutionEngine()
        self.ensemble_mode = ensemble_mode
        
        # Ensure database is initialized
        if self.db_path:
            init_db(self.db_path)
        else:
            # Let execution db pick up DEFAULT_DB_PATH
            from src.execution.database import DEFAULT_DB_PATH
            self.db_path = DEFAULT_DB_PATH
            init_db(self.db_path)

    def run_daily(self, current_date: Optional[datetime] = None) -> dict:
        """
        Runs the daily end-to-end orchestration sequence for a target date.
        Asserts timestamp freshness, aligns data causally, fits historical window,
        predicts target exposure, and persists state.
        """
        if current_date is None:
            current_date = datetime.now(timezone.utc)
        else:
            if isinstance(current_date, str):
                current_date = pd.Timestamp(current_date)
            if isinstance(current_date, datetime) and current_date.tzinfo is None:
                current_date = current_date.replace(tzinfo=timezone.utc)
            current_date = pd.Timestamp(current_date).tz_convert("UTC")

        # 1. Fetch live daily on-chain metrics & validate stamp freshness
        logger.info("Ingesting latest daily on-chain metrics...")
        feed = self.brk_ingestion.fetch_latest()
        self.brk_ingestion.validate_freshness(feed, current_date)

        # 2. Fetch daily OHLCV from Binance (guaranteeing at least 1,200 days context)
        logger.info("Fetching daily price OHLCV data...")
        df_ohlcv = ohlcv_pipeline(end_time=current_date)
        if not isinstance(df_ohlcv.index, pd.DatetimeIndex):
            df_ohlcv.index = pd.to_datetime(df_ohlcv.index)
        if df_ohlcv.index.tzinfo is None:
            df_ohlcv.index = df_ohlcv.index.tz_localize("UTC")
        df_ohlcv = df_ohlcv.sort_index()

        # 3. Fetch historical daily on-chain metrics (min 1,200 days)
        logger.info("Fetching historical daily on-chain metrics...")
        df_onchain = self.brk_ingestion.fetch_historical(lookback_days=1200)
        
        # Align latest feed into df_onchain to avoid API/sync lag discrepancy
        feed_date = pd.Timestamp(feed.stamp).normalize().tz_convert("UTC")
        df_onchain.loc[feed_date] = [
            feed.sth_mvrv,
            feed.sth_nupl,
            feed.sth_sopr_24h,
            feed.sth_supply_in_profit
        ]
        df_onchain = df_onchain.sort_index()

        # 4. Join datasets causally using point-in-time merge_asof backward
        logger.info("Merging datasets causally...")
        df_merged = point_in_time_join(df_ohlcv, df_onchain)
        df_merged = df_merged[df_merged.index <= current_date]

        if df_merged.empty:
            raise ValueError(f"No data available up to current_date: {current_date}")

        # The target date is the last bar in the aligned dataset
        t = df_merged.index[-1]
        
        # 5. Segment into trailing 3-year history for training (1095 days in-sample)
        all_prior_idx = df_merged.index[df_merged.index < t]
        if len(all_prior_idx) >= 1095:
            train_idx = df_merged.index[(df_merged.index >= t - pd.Timedelta(days=1095)) & (df_merged.index < t)]
        else:
            logger.warning("Insufficient data for full 3-year history. Falling back to all historical bars.")
            train_idx = all_prior_idx

        if len(train_idx) < 250:
            raise ValueError(f"Insufficient training bars ({len(train_idx)}) prior to execution date {t}")

        # 6. Recalibrate OU half-life to dynamically adjust trend lookback window
        log_returns = np.log(df_merged["close"] / df_merged["close"].shift(1)).fillna(0.0)
        dynamic_lookback = estimate_ou_halflife(log_returns.loc[train_idx], min_bars=250)

        # 7. Compute indicators and features (cautiously ensuring zero lookahead)
        builder = FeatureMatrixBuilder(dynamic_lookback=dynamic_lookback)
        feature_matrix = builder.build_matrix(df_merged)

        # Define targets y for training (classification of sign of next-day returns)
        price_diff = df_merged["close"].shift(-1) - df_merged["close"]
        y = np.sign(price_diff).fillna(1.0).map({-1.0: 0, 0.0: 0, 1.0: 1})

        # 8. Layer 1: Train HMM on training window and predict today's regime
        logger.info("Running HMM Regime Inference...")
        close_train = df_merged.loc[train_idx, "close"]
        hmm_model, state_to_regime = train_hmm(close_train, window=21)
        res_regime = infer_regime(hmm_model, state_to_regime, df_merged.loc[:t, "close"], window=21)
        
        # Layer 2 overrides: Apply on-chain overrides on HMM posteriors
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            onchain_metrics[col] = float(df_merged.loc[t, col])
            
        overridden_posteriors = apply_onchain_overrides(res_regime["posteriors"], onchain_metrics)
        
        # Determine final regime classification
        final_regime = max(overridden_posteriors, key=overridden_posteriors.get)

        # 9. Layer 3: Feature Processor (VIF pruning and PCA)
        logger.info("Running VIF/PCA Feature Processor...")
        processor = FeatureProcessor()
        X_train = feature_matrix.loc[train_idx]
        y_train = y.loc[train_idx]
        X_test = feature_matrix.loc[[t]]

        processor.fit(X_train, y_train)
        X_train_proc = processor.transform(X_train)
        X_test_proc = processor.transform(X_test)

        # 10. Layer 4: Ensemble model fitting and final score prediction
        if self.ensemble_mode == "pca_consensus":
            logger.info("Fitting PCA Consensus Weighted Aggregator...")
            from src.ensemble.model import PCAConsensusEnsemble
            model = PCAConsensusEnsemble()
            if processor.pca is not None:
                model.fit(
                    X=X_train,
                    pca_components_matrix=processor.pca.pca.components_,
                    kept_cols=processor.kept_tech_cols
                )
                final_score = float(model.predict_score(X_test).iloc[0])
            else:
                model.fit(X=X_train)
                final_score = float(model.predict_score(X_test).iloc[0])
        else:
            logger.info("Fitting L1-Lasso Logistic Regression model...")
            model = L1LassoEnsemble()
            model.fit(X_train_proc, y_train)
            final_score = float(model.predict_score(X_test_proc).iloc[0])

        # 11. Layer 5: Sizing exposure and persisting daily records to SQLite WAL DB
        logger.info("Executing exposure sizing and DB persistence...")
        log_ret = float(log_returns.loc[t])
        realized_vol = float(log_returns.rolling(21).std().fillna(0.0).loc[t])
        
        date_str = t.strftime("%Y-%m-%d")
        
        # Run execution engine coordinator
        exec_res = self.execution_engine.run(
            date_str=date_str,
            final_score=final_score,
            regime=final_regime,
            posteriors=overridden_posteriors,
            log_return=log_ret,
            realized_volatility=realized_vol,
            db_path=self.db_path
        )

        # Retrieve raw indicator scores and transformed PCA component values for telemetry
        indicator_scores = feature_matrix.loc[t, processor.tech_indicators_list].to_dict()
        indicator_scores = {k: int(v) if not pd.isna(v) else 0 for k, v in indicator_scores.items()}
        
        pca_cols = [c for c in X_test_proc.columns if c.startswith("PC")]
        pca_components = X_test_proc.loc[t, pca_cols].to_dict()
        pca_components = {k: float(v) for k, v in pca_components.items()}

        # Save actual cumulative PCA variance explained
        if processor.pca is not None:
            pca_variance_explained = float(np.sum(processor.pca.pca.explained_variance_ratio_)) * 100.0
            pca_components["pca_variance_explained"] = pca_variance_explained
        else:
            pca_components["pca_variance_explained"] = 100.0

        # Save actual daily VIF values
        from src.features.vif import calculate_vif
        vifs = calculate_vif(X_train)
        for ind_name, vif_val in vifs.items():
            if not pd.isna(vif_val):
                pca_components[f"VIF_{ind_name}"] = float(vif_val)

        self.execution_engine.persist_features(
            date_str=date_str,
            indicator_scores=indicator_scores,
            pca_components=pca_components,
            db_path=self.db_path
        )

        return {
            "status": "success",
            "date": date_str,
            "final_score": final_score,
            "regime": final_regime,
            "target_exposure": exec_res["target_exposure"],
            "transition_occurred": exec_res["transition_occurred"],
            "posteriors": overridden_posteriors,
            "indicator_scores": indicator_scores,
            "pca_components": pca_components
        }
