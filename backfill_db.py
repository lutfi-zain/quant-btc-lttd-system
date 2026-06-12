import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.data.pipeline import ohlcv_pipeline
from src.data.brk_ingestion_service import BRKIngestionService
from src.backtest.wfo import point_in_time_join
from src.regime.hmm import train_hmm, infer_regime
from src.features.builder import FeatureMatrixBuilder
from src.features.ou_calibration import estimate_ou_halflife
from src.features.processor import FeatureProcessor
from src.ensemble.model import L1LassoEnsemble
from src.execution.engine import ExecutionEngine
from src.execution.database import init_db, DEFAULT_DB_PATH
from src.regime.filter import apply_onchain_overrides

def backfill():
    db_path = DEFAULT_DB_PATH
    init_db(db_path)
    
    print("Fetching daily price OHLCV data...")
    df_ohlcv = ohlcv_pipeline()
    
    print("Fetching historical daily on-chain metrics...")
    ingestion = BRKIngestionService()
    df_onchain = ingestion.fetch_historical(lookback_days=1200)
    
    print("Merging datasets causally...")
    df_merged = point_in_time_join(df_ohlcv, df_onchain)
    
    # We want to backfill the last 90 days.
    end_date = df_merged.index[-1]
    start_date = end_date - pd.Timedelta(days=90)
    backfill_idx = df_merged.index[(df_merged.index >= start_date) & (df_merged.index <= end_date)]
    
    print(f"Running backfill from {backfill_idx[0].strftime('%Y-%m-%d')} to {backfill_idx[-1].strftime('%Y-%m-%d')} ({len(backfill_idx)} days)...")
    
    execution_engine = ExecutionEngine()
    log_returns = np.log(df_merged["close"] / df_merged["close"].shift(1)).fillna(0.0)
    
    # Pre-clean DB tables first to avoid duplicates
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM daily_lttd;")
    conn.execute("DELETE FROM indicator_scores;")
    conn.execute("DELETE FROM pca_components;")
    conn.execute("DELETE FROM regime_transitions;")
    conn.commit()
    conn.close()
    
    for i, t in enumerate(backfill_idx):
        date_str = t.strftime("%Y-%m-%d")
        print(f"Processing {date_str} ({i+1}/{len(backfill_idx)})...")
        
        # Segment into trailing 3-year history for training (1095 days)
        all_prior_idx = df_merged.index[df_merged.index < t]
        if len(all_prior_idx) >= 1095:
            train_idx = df_merged.index[(df_merged.index >= t - pd.Timedelta(days=1095)) & (df_merged.index < t)]
        else:
            train_idx = all_prior_idx
            
        if len(train_idx) < 250:
            print(f"Skipping {date_str}: insufficient training bars")
            continue
            
        # Recalibrate OU half-life
        dynamic_lookback = estimate_ou_halflife(log_returns.loc[train_idx], min_bars=250)
        
        # Compute indicators
        builder = FeatureMatrixBuilder(dynamic_lookback=dynamic_lookback)
        feature_matrix = builder.build_matrix(df_merged.loc[:t])
        
        # Target y
        price_diff = df_merged["close"].shift(-1) - df_merged["close"]
        y = np.sign(price_diff).fillna(1.0).map({-1.0: 0, 0.0: 0, 1.0: 1})
        
        # Train HMM and predict regime
        close_train = df_merged.loc[train_idx, "close"]
        hmm_model, state_to_regime = train_hmm(close_train, window=21)
        res_regime = infer_regime(hmm_model, state_to_regime, df_merged.loc[:t, "close"], window=21)
        
        # Apply overrides
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            onchain_metrics[col] = float(df_merged.loc[t, col])
        overridden_posteriors = apply_onchain_overrides(res_regime["posteriors"], onchain_metrics)
        
        if overridden_posteriors["BULL"] > 0.70:
            final_regime = "BULL"
        else:
            if overridden_posteriors["BEAR"] >= overridden_posteriors["SIDEWAYS"]:
                final_regime = "BEAR"
            else:
                final_regime = "SIDEWAYS"
                
        # Feature processor
        processor = FeatureProcessor()
        # Purge training set adjacent to execution date t to prevent target leakage
        train_idx_purged = train_idx[train_idx < t - pd.Timedelta(days=7)]
        X_train = feature_matrix.loc[train_idx_purged]
        y_train = y.loc[train_idx_purged]
        X_test = feature_matrix.loc[[t]]
        
        processor.fit(X_train, y_train)
        X_train_proc = processor.transform(X_train)
        X_test_proc = processor.transform(X_test)
        
        # Fit model and predict
        model = L1LassoEnsemble()
        model.fit(X_train_proc, y_train)
        final_score = float(model.predict_score(X_test_proc).iloc[0])
        
        log_ret = float(log_returns.loc[t])
        realized_vol = float(log_returns.rolling(21).std().fillna(0.0).loc[t])
        
        # Run execution engine and persist
        exec_res = execution_engine.run(
            date_str=date_str,
            final_score=final_score,
            regime=final_regime,
            posteriors=overridden_posteriors,
            log_return=log_ret,
            realized_volatility=realized_vol,
            db_path=db_path
        )
        
        indicator_scores = feature_matrix.loc[t, processor.tech_indicators_list].to_dict()
        indicator_scores = {k: int(v) if not pd.isna(v) else 0 for k, v in indicator_scores.items()}
        
        pca_cols = [c for c in X_test_proc.columns if c.startswith("PC")]
        pca_components = X_test_proc.loc[t, pca_cols].to_dict()
        pca_components = {k: float(v) for k, v in pca_components.items()}
        
        execution_engine.persist_features(
            date_str=date_str,
            indicator_scores=indicator_scores,
            pca_components=pca_components,
            db_path=db_path
        )
        
    print("✓ Backfill completed successfully.")

if __name__ == "__main__":
    backfill()
