#!/usr/bin/env python3
import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tmp.evaluate_baseline_correct import load_data, simulate_exposures

def main():
    df = load_data()
    
    conn = sqlite3.connect("database/lttd.db")
    db_df = pd.read_sql("SELECT date, target_exposure FROM daily_lttd ORDER BY date", conn, parse_dates=["date"])
    conn.close()
    
    db_df.set_index("date", inplace=True)
    
    baseline_params = {
        "entry_p": 8,
        "exit_p": 5,
        "score_entry": 0.3591637228998046,
        "score_exit": 0.32448227800286483,
        "cb_activate": -2.8290154952614124,
        "cb_cooloff": 0.7123354436183149,
        "rco_days": 4,
        "mhp_days": 12,
        "use_bear_override": False,
        "use_ma_filter": True,
        "ma_period": 229
    }
    
    sim_exposures = simulate_exposures(df, baseline_params)
    df["sim_exposure"] = sim_exposures
    df = df.join(db_df, rsuffix="_db")
    
    diff = df[df["sim_exposure"] != df["target_exposure"]]
    print(f"Number of differences: {len(diff)}")
    if len(diff) > 0:
        print("First 20 differences:")
        print(diff[["close", "final_score", "composite_value", "sim_exposure", "target_exposure"]].head(20))

if __name__ == "__main__":
    main()
