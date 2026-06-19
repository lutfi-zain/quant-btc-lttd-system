#!/usr/bin/env python3
import sqlite3
import numpy as np
import pandas as pd
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tmp.evaluate_baseline_correct import calculate_metrics_react, load_data, precompute_caches, simulate_exposures

def main():
    print("Loading data...")
    df, ohlcv_df = load_data()
    
    # Precompute caches
    entry_cache, exit_cache, ma_cache = precompute_caches(df, ohlcv_df)
    
    candidates = []
    
    print("\nRunning random search for Pareto frontier analysis (100,000 iterations)...")
    np.random.seed(42)
    for iteration in range(100000):
        params = {
            "entry_p": int(np.random.randint(4, 30)),
            "exit_p": int(np.random.randint(2, 20)),
            "score_entry": float(np.random.uniform(0.28, 0.55)),
            "score_exit": float(np.random.uniform(0.18, 0.40)),
            "cb_activate": float(np.random.uniform(-3.5, -2.0)),
            "cb_cooloff": float(np.random.uniform(0.5, 1.1)),
            "rco_days": int(np.random.randint(1, 9)),
            "mhp_days": int(np.random.randint(3, 20)),
            "use_bear_override": False,
            "use_ma_filter": True,
            "ma_period": int(np.random.randint(120, 300))
        }
        
        if params["entry_p"] <= params["exit_p"]:
            continue
        if params["score_entry"] <= params["score_exit"]:
            continue
        if params["cb_cooloff"] <= params["cb_activate"]:
            continue
            
        exps = simulate_exposures(df, params, entry_cache, exit_cache, ma_cache)
        m = calculate_metrics_react(df, exps)
        
        if m["win_rate"] >= 70.0:
            candidates.append((params, m))
            
    print(f"\nFound {len(candidates)} candidates with Win Rate >= 70.0%")
    
    if len(candidates) > 0:
        # Sort by strategy_return desc
        candidates.sort(key=lambda x: x[1]["strategy_return"], reverse=True)
        print("\n--- TOP 40 CANDIDATES BY RETURN (Win Rate >= 70%) ---")
        for idx, (p, m) in enumerate(candidates[:40]):
            print(f"#{idx+1:02d}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:,.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Sortino={m['sortino']:.2f} | Trades={m['total_trades']}")
            print(f"      Params: entry_p={p['entry_p']}, exit_p={p['exit_p']}, score_entry={p['score_entry']:.3f}, score_exit={p['score_exit']:.3f}, cb_act={p['cb_activate']:.2f}, cb_cool={p['cb_cooloff']:.2f}, rco={p['rco_days']}, mhp={p['mhp_days']}, ma={p['ma_period']}")
            
        # Write results to json
        with open("tmp/pareto_frontier_results.json", "w") as f:
            json.dump([{"params": p, "metrics": m} for p, m in candidates[:50]], f, indent=2)
    else:
        print("No candidates with Win Rate >= 70% found.")

if __name__ == "__main__":
    main()
