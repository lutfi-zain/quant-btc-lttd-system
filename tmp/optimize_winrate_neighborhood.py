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
    
    # Precompute caches (increase bounds to cover Ma up to 300, entry up to 15, exit up to 10)
    entry_cache = {}
    for p in range(3, 20):
        entry_cache[p] = super_smoother(df["final_score"], p).values

    exit_cache = {}
    for p in range(2, 15):
        exit_cache[p] = super_smoother(df["final_score"], p).values

    ma_cache = {}
    for p in range(50, 300):
        ma_full = ohlcv_df["close"].rolling(p).mean()
        ma_cache[p] = df.join(ma_full.to_frame("ma"), how="left")["ma"].values
        
    # Baseline user constraints
    min_return = 50271.16
    max_dd_limit = 38.26
    min_sharpe = 1.536
    min_sortino = 2.50
    target_winrate = 70.0
    
    # Grid search around Candidate #01
    # entry_p=7, exit_p=5, score_entry=0.320, score_exit=0.311, cb_act=-3.45, cb_cool=0.85, rco=1, mhp=12, ma=156
    
    entry_p_grid = [6, 7, 8]
    exit_p_grid = [4, 5, 6]
    score_entry_grid = [0.31, 0.32, 0.33]
    score_exit_grid = [0.30, 0.31, 0.32]
    cb_act_grid = [-3.5, -3.45, -3.4]
    cb_cool_grid = [0.8, 0.85, 0.9]
    rco_grid = [1, 2]
    mhp_grid = [11, 12, 13]
    ma_grid = [150, 156, 160]
    
    print("\nRunning neighborhood grid search...")
    valid = []
    
    for ep in entry_p_grid:
        for ex in exit_p_grid:
            if ep <= ex:
                continue
            for se in score_entry_grid:
                for sx in score_exit_grid:
                    if se <= sx:
                        continue
                    for cb_act in cb_act_grid:
                        for cb_cool in cb_cool_grid:
                            if cb_cool <= cb_act:
                                continue
                            for rco in rco_grid:
                                for mhp in mhp_grid:
                                    for ma in ma_grid:
                                        params = {
                                            "entry_p": ep,
                                            "exit_p": ex,
                                            "score_entry": float(se),
                                            "score_exit": float(sx),
                                            "cb_activate": float(cb_act),
                                            "cb_cooloff": float(cb_cool),
                                            "rco_days": rco,
                                            "mhp_days": mhp,
                                            "use_bear_override": False,
                                            "use_ma_filter": True,
                                            "ma_period": ma
                                        }
                                        
                                        exps = simulate_exposures(df, params, entry_cache, exit_cache, ma_cache)
                                        m = calculate_metrics_react(df, exps)
                                        
                                        if (
                                            m["win_rate"] >= target_winrate and
                                            m["strategy_return"] >= min_return and
                                            m["max_dd"] <= max_dd_limit and
                                            m["sharpe"] >= min_sharpe and
                                            m["sortino"] >= min_sortino
                                        ):
                                            valid.append((params, m))
                                            
    print(f"\nFound {len(valid)} exact candidate(s) that meet ALL constraints:")
    
    if len(valid) > 0:
        valid.sort(key=lambda x: (x[1]["win_rate"], x[1]["cagr"]), reverse=True)
        for idx, (p, m) in enumerate(valid[:10]):
            print(f"#{idx+1:02d}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:,.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Sortino={m['sortino']:.2f} | Trades={m['total_trades']}")
            print(f"      Params: entry_p={p['entry_p']}, exit_p={p['exit_p']}, score_entry={p['score_entry']:.3f}, score_exit={p['score_exit']:.3f}, cb_act={p['cb_activate']:.2f}, cb_cool={p['cb_cooloff']:.2f}, rco={p['rco_days']}, mhp={p['mhp_days']}, ma={p['ma_period']}")
            
        with open("tmp/optimize_winrate_results.json", "w") as f:
            json.dump({"params": valid[0][0], "metrics": valid[0][1]}, f, indent=2)
    else:
        print("No exact matches found in local grid search.")
        
def super_smoother(series: pd.Series, period: int) -> pd.Series:
    if len(series) < 2:
        return series
    
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    
    values = series.values
    out = np.zeros_like(values)
    out[0] = values[0]
    out[1] = values[1]
    
    for t in range(2, len(values)):
        out[t] = c1 * (values[t] + values[t-1]) / 2.0 + c2 * out[t-1] + c3 * out[t-2]
        
    return pd.Series(out, index=series.index)

if __name__ == "__main__":
    main()
