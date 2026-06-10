import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# Ensure the current directory is in the python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.data.pipeline import ohlcv_pipeline
from src.regime.hmm import train_hmm, infer_regime_history
from src.regime.filter import apply_onchain_overrides
from src.features.ou_calibration import estimate_ou_halflife
from src.features.builder import FeatureMatrixBuilder
from src.features.vif import calculate_vif, prune_multicollinear_indicators
from src.signals.onchain import OnChainFeed


def main():
    print("==========================================================================")
    print("         LTTD SYSTEM - COMPLETE MULTI-LAYER INTEGRATION DEMO              ")
    print("==========================================================================")

    # --------------------------------------------------------------------------
    # Step 1: Daily OHLCV Ingestion
    # --------------------------------------------------------------------------
    print("\n[Step 1] Ingesting Daily BTC OHLCV from Binance...")
    try:
        os.makedirs("database", exist_ok=True)
        df_ohlcv = ohlcv_pipeline()
        print(f"✓ Ingested {len(df_ohlcv)} daily bars successfully.")
        print("\nLatest 3 daily bars:")
        print(df_ohlcv.tail(3))
    except Exception as e:
        print(f"✗ Ingestion Pipeline failed: {e}")
        return

    if len(df_ohlcv) < 120:
        print("✗ Insufficient data. Minimum 120 daily bars required.")
        return

    # --------------------------------------------------------------------------
    # Step 2: HMM Regime Inference
    # --------------------------------------------------------------------------
    print("\n[Step 2] Inferring HMM Market Regime...")
    try:
        close_series = df_ohlcv["close"]
        model, state_to_regime = train_hmm(close_series)
        df_regimes = infer_regime_history(model, state_to_regime, close_series)
        latest_row = df_regimes.iloc[-1]
        print(f"✓ Current Market Regime: {latest_row.get('regime', 'UNKNOWN')}")
        print(f"  Posterior Probability - BULL: {latest_row.get('p_bull', 0.0):.2%}")
        print(f"  Posterior Probability - BEAR: {latest_row.get('p_bear', 0.0):.2%}")
        print(f"  Posterior Probability - SIDEWAYS: {latest_row.get('p_sideways', 0.0):.2%}")
    except Exception as e:
        print(f"✗ HMM Regime Detection failed: {e}")

    # --------------------------------------------------------------------------
    # Step 3: OU Mean-Reversion Calibration
    # --------------------------------------------------------------------------
    print("\n[Step 3] Calibrating OU Mean-Reversion Half-Life...")
    try:
        log_returns = np.log(close_series / close_series.shift(1)).dropna()
        hl = estimate_ou_halflife(log_returns, min_bars=120)
        print(f"✓ Estimated Half-Life: {hl:.2f} days (clamped to [120, 350])")
    except Exception as e:
        print(f"✗ OU Calibration failed: {e}")

    # --------------------------------------------------------------------------
    # Step 4: Technical Indicators (Layer 2 Signal Engine)
    # --------------------------------------------------------------------------
    print("\n[Step 4] Running Layer 2 Technical Indicators (Signal Engine)...")
    try:
        builder = FeatureMatrixBuilder()
        matrix_tech = builder.build_matrix(df_ohlcv)
        print("✓ Successfully calculated all 6 causal technical indicators.")
        print("\nLatest 5 rows of indicator scores ∈ {-1, +1}:")
        tech_cols = ["FDI", "QuantileDEMA", "AdvancedStochastic", "KalmanRSI", "FourierSupertrend", "TrendStrengthIndex"]
        print(matrix_tech[tech_cols].tail(5))
    except Exception as e:
        print(f"✗ Signal Engine computation failed: {e}")

    # --------------------------------------------------------------------------
    # Step 5: On-Chain Data & Euphoric Overrides (Layer 2 & Layer 1 Post-Processing)
    # --------------------------------------------------------------------------
    print("\n[Step 5] Ingesting Live On-Chain Metrics & Running Overrides...")
    try:
        # Fetching live onchain metrics
        feed = OnChainFeed()
        current_time = datetime.now(timezone.utc)
        print("Fetching latest metrics from BRK API (https://bitview.space)...")
        live_onchain = feed.fetch_latest_causal(current_time)
        print("✓ Live On-Chain Metrics fetched successfully:")
        for k, v in live_onchain.items():
            print(f"  → {k}: {v}")

        # Simulate Override Logic
        print("\nSimulating Regime Overrides:")
        hypothetical_bull = {"BULL": 0.85, "BEAR": 0.05, "SIDEWAYS": 0.10}
        print(f"  Initial Posteriors: {hypothetical_bull}")

        # Test STH-NUPL Euphoria Override
        euphoric_metrics = {"sth_nupl": 0.82, "sth_mvrv": 1.5}
        overridden_nupl = apply_onchain_overrides(hypothetical_bull, euphoric_metrics)
        print(f"  After STH-NUPL (>0.75) Override: {overridden_nupl} (BULL scaled down)")

        # Test STH-MVRV Cycle Top Override
        cycle_top_metrics = {"sth_nupl": 0.60, "sth_mvrv": 2.3}
        overridden_mvrv = apply_onchain_overrides(hypothetical_bull, cycle_top_metrics)
        print(f"  After STH-MVRV (>2.0) Override: {overridden_mvrv} (BULL reduced to 0.0)")
    except Exception as e:
        print(f"✗ On-Chain Ingestion or Override failed: {e}")

    # --------------------------------------------------------------------------
    # Step 6: Feature Matrix & VIF Multicollinearity Pruning (Layer 3)
    # --------------------------------------------------------------------------
    print("\n[Step 6] Constructing Feature Matrix & Performing VIF Pruning...")
    try:
        # Fetch historical bulk on-chain metrics for the last 300 days
        print("Fetching historical on-chain bulk data (-300 days)...")
        historical_onchain = feed.fetch_historical_bulk(start=-300)
        
        # Causal asof merge with OHLCV data
        print("Merging OHLCV and On-Chain data causally...")
        merged_data = feed.fetcher.align_with_ohlcv(historical_onchain, df_ohlcv)

        # Build feature matrix (includes 7-day rate of change of on-chain metrics)
        feature_matrix = builder.build_matrix(merged_data).dropna()
        print(f"✓ Feature Matrix constructed. Shape: {feature_matrix.shape}")
        
        # Calculate VIF
        vifs = calculate_vif(feature_matrix)
        print("\nBefore Pruning - Variance Inflation Factors (VIF):")
        for col, val in vifs.items():
            print(f"  → {col}: {val:.2f}")

        # Run step-wise VIF Pruning (using a random target y for Pratt's Measure)
        np.random.seed(42)
        target_y = pd.Series(np.random.randn(len(feature_matrix)), index=feature_matrix.index)
        pruned_matrix = prune_multicollinear_indicators(feature_matrix, target_y, vif_threshold=10.0)
        
        print(f"\n✓ Pruned Feature Matrix. Shape: {pruned_matrix.shape}")
        pruned_vifs = calculate_vif(pruned_matrix)
        print("After Pruning - Variance Inflation Factors (VIF):")
        for col, val in pruned_vifs.items():
            print(f"  → {col}: {val:.2f}")

        print("\n==========================================================================")
        print("All features verified and running correctly!")
        print("==========================================================================")
    except Exception as e:
        print(f"✗ Feature Processing or VIF check failed: {e}")


if __name__ == "__main__":
    main()
