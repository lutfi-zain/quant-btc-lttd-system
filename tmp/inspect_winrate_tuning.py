#!/usr/bin/env python3
import sqlite3
import numpy as np
import pandas as pd
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tmp.evaluate_baseline_correct import load_data, simulate_exposures, calculate_metrics_react

def main():
    df = load_data()
    
    # Baseline params:
    # entry_p=8, exit_p=5, score_entry=0.359, score_exit=0.324, cb_act=-2.829, cb_cool=0.712, rco=4, mhp=12, ma=229
    
    # Let's perform a grid search on:
    # - mhp_days: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    # - rco_days: [1, 2, 3, 4, 5, 6, 7, 8]
    # - use_bear_override: [True, False]
    # - score_entry: [0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.40, 0.42]
    # - score_exit: [0.30, 0.31, 0.32, 0.33, 0.34, 0.35]
    
    print("Running grid search...")
    results = []
    
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
    
    # Run baseline first to double check
    exps = simulate_exposures(df, baseline_params)
    base_m = calculate_metrics_react(df, exps)
    print(f"Baseline: WinRate={base_m['win_rate']:.2f}% | Return={base_m['strategy_return']:.2f}% | MaxDD={base_m['max_dd']:.2f}% | Sharpe={base_m['sharpe']:.2f}")
    
    # User targets
    target_winrate = 70.0
    min_return = 50271.16
    max_dd_limit = 38.26
    min_sharpe = 1.536
    
    # We will search combinations of mhp_days, rco_days, use_bear_override, score_entry, score_exit
    count = 0
    for mhp in range(2, 16):
        for rco in range(1, 9):
            for bear in [False, True]:
                for entry_score in [0.33, 0.35, 0.37, 0.39, 0.41]:
                    for exit_score in [0.28, 0.30, 0.32, 0.34]:
                        params = baseline_params.copy()
                        params["mhp_days"] = mhp
                        params["rco_days"] = rco
                        params["use_bear_override"] = bear
                        params["score_entry"] = entry_score
                        params["score_exit"] = exit_score
                        
                        exps = simulate_exposures(df, params)
                        m = calculate_metrics_react(df, exps)
                        
                        results.append((params, m))
                        count += 1
                        
    print(f"Evaluated {count} combinations.")
    
    # Check if any met all constraints
    valid = []
    for p, m in results:
        if (
            m["win_rate"] >= target_winrate and
            m["strategy_return"] >= min_return and
            m["max_dd"] <= max_dd_limit and
            m["sharpe"] >= min_sharpe
        ):
            valid.append((p, m))
            
    print(f"\nFound {len(valid)} candidate(s) that meet ALL constraints:")
    valid.sort(key=lambda x: (x[1]["win_rate"], x[1]["cagr"]), reverse=True)
    for idx, (p, m) in enumerate(valid[:10]):
        print(f"#{idx+1}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Trades={m['total_trades']}")
        print(f"    Params: score_entry={p['score_entry']}, score_exit={p['score_exit']}, rco={p['rco_days']}, mhp={p['mhp_days']}, bear={p['use_bear_override']}")
        
    if not valid:
        print("No exact matches found. Top 10 by win rate:")
        results.sort(key=lambda x: x[1]["win_rate"], reverse=True)
        for idx, (p, m) in enumerate(results[:10]):
            print(f"#{idx+1}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Trades={m['total_trades']}")
            print(f"    Params: score_entry={p['score_entry']}, score_exit={p['score_exit']}, rco={p['rco_days']}, mhp={p['mhp_days']}, bear={p['use_bear_override']}")

if __name__ == "__main__":
    main()
