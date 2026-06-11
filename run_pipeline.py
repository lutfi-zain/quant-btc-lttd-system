import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import json

# Ensure the current directory is in the python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.pipeline import LTTDPipeline, DataStaleException

def run():
    print("==========================================================================")
    print("                LTTD SYSTEM - LIVE DATA RUN & CALCULATION                 ")
    print("==========================================================================")
    
    pipeline = LTTDPipeline()
    try:
        res = pipeline.run_daily()
        print("\n✓ Pipeline run completed successfully.")
        print("\n==========================================================================")
        print(f"LATEST CALCULATED STATE FOR TODAY ({res['date']}):")
        print(f"  Regime         : {res['regime']}")
        print(f"  Final Score    : {res['final_score']:.4f}")
        print(f"  Target Exposure: {res['target_exposure']:.4f}")
        print("  Indicator Scores:")
        for k, v in res["indicator_scores"].items():
            print(f"    - {k:20}: {v}")
        print("  PCA Orthogonalized Components:")
        for k, v in res["pca_components"].items():
            print(f"    - {k:20}: {v:.4f}")
        print("==========================================================================")
    except DataStaleException as e:
        print(f"✗ Live daily run paused: on-chain data is stale. Details: {e}")
    except Exception as e:
        print(f"✗ Pipeline run failed: {e}")

if __name__ == "__main__":
    run()
