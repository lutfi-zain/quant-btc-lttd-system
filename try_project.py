import os
import sys
import numpy as np

# Ensure the current directory is in the python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.data.pipeline import ohlcv_pipeline
from src.regime.hmm import train_hmm, infer_regime_history
from src.features.ou_calibration import estimate_ou_halflife


def main():
    print("==========================================================")
    print("         LTTD SYSTEM - INGESTION & CALIBRATION DEMO       ")
    print("==========================================================")

    # Step 1: Ingest BTC OHLCV from Binance
    print("\n[Step 1] Running daily OHLCV Ingestion Pipeline...")
    print("Fetching and caching BTC-USDT daily data from Binance API...")
    try:
        os.makedirs("database", exist_ok=True)
        # Fetch data (will cache in database/lttd.db)
        df_ohlcv = ohlcv_pipeline()
        print(f"✓ Ingested {len(df_ohlcv)} daily bars successfully.")
        print("\nLatest 5 rows of ingested OHLCV data:")
        print(df_ohlcv.tail(5))
    except Exception as e:
        print(f"✗ Ingestion Pipeline failed: {e}")
        return

    if len(df_ohlcv) < 120:
        print("✗ Insufficient data. Minimum 120 daily bars required.")
        return

    # Step 2: Fit HMM and Predict Regime Transitions
    print(
        "\n[Step 2] Training 3-state HMM Regime Detector on historical close prices..."
    )
    try:
        close_series = df_ohlcv["close"]
        model, state_to_regime = train_hmm(close_series)
        print("✓ HMM Model trained successfully (deterministically labeled states).")

        df_regimes = infer_regime_history(model, state_to_regime, close_series)
        print("✓ Historical regime inference completed.")

        print("\nLatest 5 rows of regime classification results:")
        cols = ["close", "log_returns", "realized_volatility", "regime", "prob_BULL"]
        # Filter available columns
        existing_cols = [c for c in cols if c in df_regimes.columns]
        print(df_regimes[existing_cols].tail(5))

        latest_row = df_regimes.iloc[-1]
        print(f"\n→ Current Market Regime: {latest_row.get('regime', 'UNKNOWN')}")
        if "prob_BULL" in latest_row:
            print(
                f"→ Posterior Probabilities: BULL={latest_row['prob_BULL']:.2%}, BEAR={latest_row.get('prob_BEAR', 0.0):.2%}, SIDEWAYS={latest_row.get('prob_SIDEWAYS', 0.0):.2%}"
            )
    except Exception as e:
        print(f"✗ HMM Regime Detection failed: {e}")

    # Step 3: Calibrate OU Mean Reversion Half-Life
    print("\n[Step 3] Calibrating Ornstein-Uhlenbeck (OU) Mean-Reversion Half-Life...")
    try:
        # Calculate daily log returns
        log_returns = np.log(close_series / close_series.shift(1)).dropna()
        hl = estimate_ou_halflife(log_returns, min_bars=120)
        print(
            f"✓ Estimated Mean Reversion Speed: {hl:.2f} days (clamped to LTTD window bounds [120, 350])"
        )
        print("\n==========================================================")
        print("Demo execution finished successfully!")
        print("==========================================================")
    except Exception as e:
        print(f"✗ OU Calibration failed: {e}")


if __name__ == "__main__":
    main()
