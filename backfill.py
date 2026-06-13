import pandas as pd
from datetime import timedelta, datetime, timezone
import sys
from src.pipeline import LTTDPipeline

def main():
    print("Initializing pipeline...")
    pipeline = LTTDPipeline(ensemble_mode="lasso")
    
    # Run for the last 10 days
    today = datetime.now(timezone.utc)
    
    print("Starting backfill...")
    for i in range(10, -1, -1):
        target_date = today - timedelta(days=i)
        print(f"Running pipeline for {target_date.strftime('%Y-%m-%d')}...")
        try:
            res = pipeline.run_daily(target_date)
            print(f"Success: {res['regime']} (Score: {res['final_score']:.4f})")
        except Exception as e:
            print(f"Error on {target_date}: {e}")

if __name__ == "__main__":
    main()
