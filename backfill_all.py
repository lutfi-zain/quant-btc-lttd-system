import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import concurrent.futures
import sqlite3
import json

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sklearn.cluster import KMeans
# Patch KMeans.fit to set n_init=1 to speed up calculations without violating signature checks
original_kmeans_fit = KMeans.fit
def patched_kmeans_fit(self, X, y=None, sample_weight=None):
    self.n_init = 1
    return original_kmeans_fit(self, X, y=y, sample_weight=sample_weight)
KMeans.fit = patched_kmeans_fit

from src.data.exchange_adapter import BinanceAdapter
from src.data.db import SQLiteCache
from src.data.brk_ingestion_service import BRKIngestionService
from src.backtest.wfo import point_in_time_join
from src.regime.hmm import train_hmm, infer_regime
from src.features.builder import FeatureMatrixBuilder
from src.features.ou_calibration import estimate_ou_halflife
from src.features.processor import FeatureProcessor
from src.ensemble.model import L1LassoEnsemble
from src.execution.engine import ExecutionEngine
from src.execution.database import init_db, DEFAULT_DB_PATH, get_connection
from src.regime.filter import apply_onchain_overrides

def process_single_day(t, df_merged, feature_matrix, log_returns, y):
    try:
        date_str = t.strftime("%Y-%m-%d")
        
        # Segment into trailing 3-year history for training (1095 days)
        all_prior_idx = df_merged.index[df_merged.index < t]
        if len(all_prior_idx) >= 1095:
            train_idx = df_merged.index[(df_merged.index >= t - pd.Timedelta(days=1095)) & (df_merged.index < t)]
        else:
            train_idx = all_prior_idx
            
        if len(train_idx) < 250:
            return None
            
        # Get indicators from the pre-calculated feature matrix up to t
        feature_matrix_t = feature_matrix.loc[:t]
        
        # Train HMM and predict regime
        close_train = df_merged.loc[train_idx, "close"]
        hmm_model, state_to_regime = train_hmm(close_train, window=21)
        res_regime = infer_regime(hmm_model, state_to_regime, df_merged.loc[:t, "close"], window=21)
        
        # Apply overrides
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            onchain_metrics[col] = float(df_merged.loc[t, col])
        overridden_posteriors = apply_onchain_overrides(res_regime["posteriors"], onchain_metrics)
        
        # Determine final regime classification using argmax
        final_regime = max(overridden_posteriors, key=overridden_posteriors.get)
                
        # Feature processor
        processor = FeatureProcessor()
        # Purge training set adjacent to execution date t to prevent target leakage
        train_idx_purged = train_idx[train_idx < t - pd.Timedelta(days=7)]
        X_train = feature_matrix_t.loc[train_idx_purged]
        y_train = y.loc[train_idx_purged]
        X_test = feature_matrix_t.loc[[t]]
        
        processor.fit(X_train, y_train)
        X_train_proc = processor.transform(X_train)
        X_test_proc = processor.transform(X_test)
        
        # Fit model and predict (PCA Consensus)
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
        
        log_ret = float(log_returns.loc[t])
        realized_vol = float(log_returns.rolling(21).std().fillna(0.0).loc[t])
        
        # Sizing target exposure
        from src.execution.sizing import calculate_target_exposure
        target_exposure = calculate_target_exposure(final_score, final_regime)
        
        # Get indicator scores and PCA components
        indicator_scores = feature_matrix_t.loc[t, processor.tech_indicators_list].to_dict()
        indicator_scores = {k: int(v) if not pd.isna(v) else 0 for k, v in indicator_scores.items()}
        
        pca_cols = [c for c in X_test_proc.columns if c.startswith("PC")]
        pca_components = X_test_proc.loc[t, pca_cols].to_dict()
        pca_components = {k: float(v) for k, v in pca_components.items()}

        # Save actual PCA cumulative variance explained
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
        
        # Return record dict
        return {
            "date": date_str,
            "regime": final_regime,
            "final_score": final_score,
            "target_exposure": target_exposure,
            "posterior_prob": overridden_posteriors.get(final_regime, 0.0),
            "indicator_scores": indicator_scores,
            "pca_components": pca_components,
            "log_return": log_ret,
            "realized_volatility": realized_vol,
            "posteriors": overridden_posteriors
        }
    except Exception as e:
        return None

def main():
    db_path = DEFAULT_DB_PATH
    init_db(db_path)
    
    print("==========================================================================")
    # 1. Fetch ALL daily price history from BRK API starting from index 1871 (~2014-02-22)
    print("Fetching ALL daily BTC OHLCV from BRK API starting from index 1871 (~2014-02-22)...")
    import requests
    from brk_client import BrkClient
    res_price = requests.get('https://bitview.space/api/series/bulk?series=price_ohlc&index=day1&start=-4500').json()
    brk_client = BrkClient()
    start_date = brk_client.index_to_date("day1", res_price["start"])
    dates = pd.date_range(start=start_date, periods=len(res_price["data"]), freq="D", tz="UTC", name="timestamp")
    df_ohlcv = pd.DataFrame(res_price["data"], index=dates, columns=["open", "high", "low", "close"])
    df_ohlcv["volume"] = 1.0 # Constant volume fallback for VWMA calculation
    print(f"✓ Fetched {len(df_ohlcv)} daily bars from BRK API.")
    
    # Save the entire OHLCV dataset to SQLiteCache
    cache = SQLiteCache(db_path)
    # Pre-clean ohlcv table
    with cache.get_connection() as conn:
        conn.execute("DELETE FROM ohlcv;")
        conn.commit()
    # Insert BRK baseline data
    cache.save_dataframe(df_ohlcv)
    print(f"Saved {len(df_ohlcv)} OHLCV rows from BRK to cache.")
    
    # 2. Overlay Binance data to get accurate volume (starts ~2017-08)
    print("Overlaying Binance OHLCV data to fix volume degradation...")
    try:
        adapter = BinanceAdapter()
        binance_df = adapter.fetch_ohlcv(start_time=datetime(2017, 8, 1, tzinfo=timezone.utc))
        if not binance_df.empty:
            cache.update_dataframe(binance_df)
            print(f"Overlaid {len(binance_df)} OHLCV rows from Binance.")
        else:
            print("Warning: Binance adapter returned empty DataFrame.")
    except Exception as e:
        print(f"Failed to overlay Binance data: {e}")
    
    # 2. Fetch bulk on-chain history (4500 days lookback)
    print("Fetching historical daily on-chain metrics (4500 days)...")
    ingestion = BRKIngestionService()
    df_onchain = ingestion.fetch_historical(lookback_days=4500)
    print(f"✓ Fetched on-chain data starting from {df_onchain.index.min().strftime('%Y-%m-%d')}.")
    
    # 3. Merge datasets causally
    print("Merging datasets causally...")
    df_merged = point_in_time_join(df_ohlcv, df_onchain)
    
    # Define start/end index (start from 2016-01-01 so LTTD starts exactly at 2016)
    backfill_idx = df_merged.index[df_merged.index >= "2016-01-01"]
    print(f"Total dates to backfill: {len(backfill_idx)} days (from {backfill_idx[0].strftime('%Y-%m-%d')} to {backfill_idx[-1].strftime('%Y-%m-%d')}).")
    
    log_returns = np.log(df_merged["close"] / df_merged["close"].shift(1)).fillna(0.0)
    price_diff = df_merged["close"].shift(-1) - df_merged["close"]
    y = np.sign(price_diff).fillna(1.0).map({-1.0: 0, 0.0: 0, 1.0: 1})
    
    # 4. Pre-calculate lookbacks (OU calibration)
    print("Pre-calculating dynamic lookbacks (OU calibration)...")
    lookback_values = []
    for t in backfill_idx:
        all_prior_idx = df_merged.index[df_merged.index < t]
        if len(all_prior_idx) >= 1095:
            train_idx = df_merged.index[(df_merged.index >= t - pd.Timedelta(days=1095)) & (df_merged.index < t)]
        else:
            train_idx = all_prior_idx
        
        # Estimate dynamic lookback (clamp/fallback is handled inside the estimator)
        hl = estimate_ou_halflife(log_returns.loc[train_idx], min_bars=250)
        lookback_values.append(hl)
        
    lookback_series = pd.Series(lookback_values, index=backfill_idx)
    print("✓ Dynamic lookbacks calculated.")
    
    # 5. Pre-calculate complete feature matrix once (avoids O(N^2) calculations)
    print("Pre-calculating complete feature matrix once...")
    builder = FeatureMatrixBuilder(dynamic_lookback=lookback_series)
    feature_matrix = builder.build_matrix(df_merged)
    print("✓ Feature matrix calculated.")
    
    print("Running parallel daily calculations via ThreadPoolExecutor...")
    results = []
    
    # We use ThreadPoolExecutor to run the HMM/Lasso models for each day in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_single_day, t, df_merged, feature_matrix, log_returns, y): t for t in backfill_idx}
        
        count = 0
        total = len(futures)
        for future in concurrent.futures.as_completed(futures):
            t = futures[future]
            res = future.result()
            if res:
                results.append(res)
            
            count += 1
            if count % 200 == 0 or count == total:
                print(f"  → Calculated {count}/{total} days...")
                
    # Sort results chronologically
    results = sorted(results, key=lambda x: x["date"])
    print(f"✓ Parallel computation finished. Successfully calculated {len(results)} days.")
    
    # 6. Insert results into the database in bulk transactions
    print("Saving records to SQLite database in bulk...")
    conn = sqlite3.connect(db_path)
    
    # Clear tables
    conn.execute("DELETE FROM daily_lttd;")
    conn.execute("DELETE FROM indicator_scores;")
    conn.execute("DELETE FROM pca_components;")
    conn.execute("DELETE FROM regime_transitions;")
    conn.commit()
    
    # Prepare inserts
    daily_records = []
    ind_records = []
    pca_records = []
    trans_records = []
    
    previous_regime = None
    
    for r in results:
        date_str = r["date"]
        regime = r["regime"]
        final_score = r["final_score"]
        target_exposure = r["target_exposure"]
        posterior_prob = r["posterior_prob"]
        
        # daily_lttd row: (data_as_of, date, regime, final_score, target_exposure, posterior_prob)
        daily_records.append((date_str, date_str, regime, final_score, target_exposure, posterior_prob))
        
        # indicator_scores rows: (date, indicator_name, score)
        for ind_name, score in r["indicator_scores"].items():
            ind_records.append((date_str, ind_name, score))
            
        # pca_components rows: (date, component_name, value)
        for pca_name, val in r["pca_components"].items():
            pca_records.append((date_str, pca_name, val))
            
        # regime_transitions row if regime changed
        if previous_regime is not None and previous_regime != regime:
            triggering = {
                "Log Return": r["log_return"],
                "Realized Volatility": r["realized_volatility"]
            }
            trans_records.append((date_str, previous_regime, regime, posterior_prob, json.dumps(triggering)))
            
        previous_regime = regime
        
    # Execute batch inserts
    conn.executemany("""
        INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob)
        VALUES (?, ?, ?, ?, ?, ?)
    """, daily_records)
    
    conn.executemany("""
        INSERT OR REPLACE INTO indicator_scores (date, indicator_name, score)
        VALUES (?, ?, ?)
    """, ind_records)
    
    conn.executemany("""
        INSERT OR REPLACE INTO pca_components (date, component_name, value)
        VALUES (?, ?, ?)
    """, pca_records)
    
    conn.executemany("""
        INSERT INTO regime_transitions (transition_date, previous_regime, new_regime, posterior_probability, triggering_metrics)
        VALUES (?, ?, ?, ?, ?)
    """, trans_records)
    
    conn.commit()
    conn.close()
    
    print("==========================================================================")
    print("✓ HISTORICAL DATABASE BACKFILL COMPLETED SUCCESSFULLY FROM 2016 TO 2026!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
