import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import json

# Ensure the current directory is in the python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.data.pipeline import ohlcv_pipeline
from src.regime.hmm import train_hmm, infer_regime_history
from src.regime.filter import apply_onchain_overrides
from src.features.builder import FeatureMatrixBuilder
from src.features.processor import FeatureProcessor
from src.signals.onchain import OnChainFeed
from src.execution.db import init_db, DEFAULT_DB_PATH
from src.execution.persistence import (
    upsert_daily_lttd,
    upsert_indicator_scores,
    log_regime_transition,
    upsert_pca_components
)

def run():
    print("==========================================================================")
    print("                LTTD SYSTEM - LIVE DATA RUN & CALCULATION                 ")
    print("==========================================================================")
    
    # 1. Initialize SQLite Database Tables
    print("\n[1/6] Initializing Database Schema...")
    init_db()
    print("✓ Schema initialized successfully.")

    # 2. Fetch and Cache Daily BTC OHLCV from Binance
    print("\n[2/6] Fetching latest BTC OHLCV data from Binance...")
    df_ohlcv = ohlcv_pipeline()
    print(f"✓ Total available daily bars: {len(df_ohlcv)}")
    print(f"  Range: {df_ohlcv.index[0].date()} to {df_ohlcv.index[-1].date()}")

    if len(df_ohlcv) < 120:
        print("✗ Insufficient data. HMM regime detection requires at least 120 bars.")
        return

    # 3. Train HMM Model and Infer Regime History
    print("\n[3/6] Inferring HMM Market Regime historically...")
    close_series = df_ohlcv["close"]
    model, state_to_regime = train_hmm(close_series)
    df_regimes = infer_regime_history(model, state_to_regime, close_series)
    print(f"✓ HMM history inferred for {len(df_regimes)} bars.")

    # 4. Fetch Deep On-Chain Metrics (1000 days history)
    print("\n[4/6] Fetching historical on-chain metrics from BRK API (https://bitview.space)...")
    feed = OnChainFeed()
    try:
        historical_onchain = feed.fetch_historical_bulk(start=-1100)
        print(f"✓ Fetched {len(historical_onchain)} rows of bulk on-chain data.")
        merged_data = feed.fetcher.align_with_ohlcv(historical_onchain, df_ohlcv)
        print("✓ Merged OHLCV and On-Chain data causally.")
    except Exception as e:
        print(f"⚠ Warning: Could not fetch on-chain history ({e}). Proceeding with neutral values.")
        merged_data = df_ohlcv.copy()
        for col in feed.series_list:
            merged_data[col] = np.nan

    # 5. Compute Layer 2 Technical Indicators
    print("\n[5/6] Calculating all 6 causal technical indicator scores...")
    builder = FeatureMatrixBuilder()
    feature_matrix = builder.build_matrix(merged_data)
    print("✓ Technical indicators calculated.")

    # 6. Process calculations chronologically and save to SQLite
    print("\n[6/6] Processing chronological calculation loop and writing to database...")
    
    # We will process dates that are in both HMM output and indicator matrix
    common_dates = df_regimes.index.intersection(feature_matrix.index).sort_values()
    print(f"  Processing {len(common_dates)} daily records...")

    tech_cols = [
        "FDI", "QuantileDEMA", "AdvancedStochastic",
        "KalmanRSI", "FourierSupertrend", "TrendStrengthIndex"
    ]

    previous_regime = None
    records_saved = 0
    transitions_logged = 0
    pca_records_saved = 0

    for idx, date in enumerate(common_dates):
        date_str = date.strftime("%Y-%m-%d")
        
        # A. Technical Indicator Scores
        scores = {}
        for col in tech_cols:
            val = feature_matrix.loc[date, col]
            scores[col] = int(val) if not pd.isna(val) else -1
        
        # B. Get HMM Posteriors
        p_bull = float(df_regimes.loc[date, "p_bull"])
        p_bear = float(df_regimes.loc[date, "p_bear"])
        p_sideways = float(df_regimes.loc[date, "p_sideways"])
        posteriors = {"BULL": p_bull, "BEAR": p_bear, "SIDEWAYS": p_sideways}

        # C. Get On-Chain metrics for overrides
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            if col in merged_data.columns:
                val = merged_data.loc[date, col]
                onchain_metrics[col] = float(val) if not pd.isna(val) else 0.0
            else:
                onchain_metrics[col] = 0.0

        # D. Apply overrides
        overridden_posteriors = apply_onchain_overrides(posteriors, onchain_metrics)

        # E. Final regime classification with 0.70 threshold for BULL
        if overridden_posteriors["BULL"] > 0.70:
            final_regime = "BULL"
        else:
            if overridden_posteriors["BEAR"] >= overridden_posteriors["SIDEWAYS"]:
                final_regime = "BEAR"
            else:
                final_regime = "SIDEWAYS"

        # F. Calculate temporary consensus Final Score (average of indicator scores)
        final_score = float(np.mean(list(scores.values())))

        # G. Write indicator scores to SQLite
        upsert_indicator_scores(date_str, scores)

        # H. Calculate and Write PCA components (causally fit on trailing history)
        # We need at least 30 bars of history to fit scaling and PCA stably
        if idx >= 30:
            train_dates = common_dates[:idx]
            train_df = feature_matrix.loc[train_dates]
            
            # Initialize and fit FeatureProcessor
            processor = FeatureProcessor()
            processor.fit(train_df)
            
            # Transform the current single row
            transformed_row = processor.transform(feature_matrix.loc[[date]])
            
            # Extract PC components
            pca_cols = [c for c in transformed_row.columns if c.startswith("PC")]
            pca_vals = {col: float(transformed_row.loc[date, col]) for col in pca_cols}
            
            # Upsert PCA components to SQLite
            upsert_pca_components(date_str, pca_vals)
            pca_records_saved += 1
            
            # Store the latest pca_vals for final printout
            if idx == len(common_dates) - 1:
                latest_pca_vals = pca_vals

        # I. Write daily LTTD to SQLite
        upsert_daily_lttd(date_str, final_regime, final_score)
        records_saved += 1

        # J. Detect and log transitions
        if final_regime != previous_regime:
            triggering_metrics = {
                "sth_mvrv": onchain_metrics["sth_mvrv"],
                "sth_nupl": onchain_metrics["sth_nupl"],
                "raw_posteriors": posteriors,
                "overridden_posteriors": overridden_posteriors
            }
            triggering_str = json.dumps(triggering_metrics)
            log_regime_transition(
                transition_date=date_str,
                previous_regime=previous_regime,
                new_regime=final_regime,
                posterior_probability=overridden_posteriors[final_regime],
                triggering_metrics=triggering_str
            )
            transitions_logged += 1
            print(f"  → Transition detected on {date_str}: {previous_regime} → {final_regime} "
                  f"(Prob: {overridden_posteriors[final_regime]:.2%})")

        previous_regime = final_regime

    print(f"\n✓ Saved {records_saved} daily LTTD and indicator records successfully.")
    print(f"✓ Saved {pca_records_saved} daily PCA orthogonalized component sets successfully.")
    print(f"✓ Logged {transitions_logged} regime transitions.")
    
    # Print latest record status
    latest_date = common_dates[-1]
    latest_date_str = latest_date.strftime("%Y-%m-%d")
    print("\n==========================================================================")
    print(f"LATEST CALCULATED STATE FOR TODAY ({latest_date_str}):")
    print(f"  Regime      : {previous_regime}")
    print(f"  Final Score : {float(np.mean([feature_matrix.loc[latest_date, col] for col in tech_cols])):.4f}")
    print("  Indicator Scores:")
    for col in tech_cols:
        print(f"    - {col:20}: {int(feature_matrix.loc[latest_date, col])}")
    if 'latest_pca_vals' in locals():
        print("  PCA Orthogonalized Components:")
        for k, v in latest_pca_vals.items():
            print(f"    - {k:20}: {v:.4f}")
    print("==========================================================================")

if __name__ == "__main__":
    run()
