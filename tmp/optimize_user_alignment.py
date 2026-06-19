import sqlite3
import pandas as pd
import numpy as np
from scipy.optimize import differential_evolution
import json
import os, sys

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    df.set_index("date", inplace=True)
    
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is not None:
        val_df = val_df.copy()
        val_df["date"] = pd.to_datetime(val_df["date"])
        if val_df["date"].dt.tz is not None:
            val_df["date"] = val_df["date"].dt.tz_convert(None)
        val_df.set_index("date", inplace=True)
        df = df.join(val_df[["composite_value"]], how="left")
    df["composite_value"] = df["composite_value"].fillna(0.0)
    return df

def get_user_target_exposure(dates):
    target = pd.Series(0.0, index=dates)
    
    # Rule 1 & 2: Bull market 2017
    # Entry July 29, 2017 to exit Jan 10, 2018
    target.loc["2017-07-29":"2018-01-10"] = 1.0
    
    # Rule 5: Jan 10, 2020 to Mar 4, 2020
    target.loc["2020-01-10":"2020-03-04"] = 1.0
    
    # Rule 6: Mar 16, 2020 to Apr 27, 2021 (no cut loss in Sept)
    target.loc["2020-03-16":"2021-04-27"] = 1.0
    
    # Rule 8: July 23, 2021 to Nov 28, 2021
    target.loc["2021-07-23":"2021-11-28"] = 1.0
    
    # Rule 11 & 12: Oct 22, 2023 to Apr 15, 2024
    target.loc["2023-10-22":"2024-04-15"] = 1.0
    
    # Rule 14: Oct 1, 2024 to Feb 15, 2025
    target.loc["2024-10-01":"2025-02-15"] = 1.0
    
    # Rule 17: Apr 20, 2025 to Oct 23, 2025
    target.loc["2025-04-20":"2025-10-23"] = 1.0
    
    return target

def simulate_binary(df, params):
    ema_entry = params["ema_span_entry"]
    ema_exit = params["ema_span_exit"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    use_bear = params["use_bear_override"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    comp_entry_boost = params.get("comp_entry_boost", 99.0)
    
    smoothed_entry = df["final_score"].ewm(span=ema_entry, adjust=False).mean()
    smoothed_exit = df["final_score"].ewm(span=ema_exit, adjust=False).mean()
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    
    for i in range(len(df)):
        score_ent = smoothed_entry.iloc[i]
        score_ex = smoothed_exit.iloc[i]
        regime = df["regime"].iloc[i]
        comp = df["composite_value"].iloc[i]
        
        exp = prev_exp
        
        # Valuation Circuit Breaker
        if cb_active:
            if comp > cb_cooloff:
                cb_active = False
            else:
                exposures[i] = 0.0
                prev_exp = 0.0
                continue
        else:
            if comp <= cb_activate:
                cb_active = True
                exposures[i] = 0.0
                prev_exp = 0.0
                continue
        
        # Score-based entry/exit
        if prev_exp >= 0.9:  # currently IN
            if score_ex <= score_exit:
                exp = 0.0
        else:  # currently OUT
            if score_ent >= score_entry:
                exp = 1.0
        
        # BEAR regime override
        if use_bear and regime == "BEAR":
            exp = 0.0
            
        # Composite value entry boost (accumulation)
        if comp >= comp_entry_boost and exp == 0.0:
            exp = 1.0
        
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

def objective(x, df, target_exposure):
    ema_span_entry = max(2, int(round(x[0])))
    ema_span_exit = max(2, int(round(x[1])))
    score_entry = x[2]
    score_exit = x[3]
    cb_activate = x[4]
    cb_cooloff = x[5]
    use_bear = x[6] > 0.5
    
    # Ensure entry span is slower or equal to exit span
    if ema_span_entry < ema_span_exit:
        return 1e6
    
    # Ensure hysteresis: entry > exit
    if score_entry <= score_exit:
        return 1e6
    
    # Ensure CB hysteresis: cooloff > activate
    if cb_cooloff <= cb_activate:
        return 1e6
    
    params = {
        "ema_span_entry": ema_span_entry,
        "ema_span_exit": ema_span_exit,
        "score_entry": score_entry,
        "score_exit": score_exit,
        "use_bear_override": use_bear,
        "cb_activate": cb_activate,
        "cb_cooloff": cb_cooloff,
        "comp_entry_boost": 99.0, # Disable deep value accumulation boost per user rules
    }
    
    try:
        sim_exposure = simulate_binary(df, params)
        
        # Loss function: mismatch penalty + trade count penalty
        # False positives (trading when user says no trade) are bad
        # False negatives (not trading when user says trade) are bad
        diff = sim_exposure - target_exposure.values
        mismatch_loss = np.sum(np.abs(diff))
        
        # Count trades
        trades = np.sum(np.diff(sim_exposure) != 0)
        
        # Penalize if too many trades (avoid whipsaws/noise)
        trade_penalty = max(0, trades - 14) * 50.0  # target is around 14 trades (7 entries, 7 exits)
        
        # Penalize if too few trades
        if trades < 6:
            trade_penalty += 5000.0
            
        return mismatch_loss + trade_penalty
        
    except Exception:
        return 1e6

def main():
    print("Loading data...")
    df = load_data()
    target_exposure = get_user_target_exposure(df.index)
    
    # Parameter bounds:
    # [ema_span_entry, ema_span_exit, score_entry, score_exit, cb_activate, cb_cooloff, use_bear]
    bounds = [
        (5, 50),         # ema_span_entry
        (2, 20),         # ema_span_exit
        (0.10, 0.90),    # score_entry
        (-0.20, 0.60),   # score_exit
        (-3.0, -0.5),    # cb_activate
        (-1.0, 1.0),     # cb_cooloff
        (0.0, 1.0),      # use_bear
    ]
    
    print("\nOptimizing parameters for USER ALIGNMENT...")
    result = differential_evolution(
        objective,
        bounds,
        args=(df, target_exposure),
        maxiter=100,
        popsize=30,
        tol=1e-6,
        seed=42,
        disp=True,
        workers=1,
    )
    
    x = result.x
    best_params = {
        "ema_span_entry": max(2, int(round(x[0]))),
        "ema_span_exit": max(2, int(round(x[1]))),
        "score_entry": x[2],
        "score_exit": x[3],
        "use_bear_override": bool(x[6] > 0.5),
        "cb_activate": x[4],
        "cb_cooloff": x[5],
        "comp_entry_boost": 99.0, # disabled
    }
    
    print(f"\n{'='*60}")
    print(f"BEST USER-ALIGNED PARAMETERS:")
    print(f"{'='*60}")
    for k, v in best_params.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.6f}")
        else:
            print(f"  {k}: {v}")
            
    # Simulate best
    sim_exposure = simulate_binary(df, best_params)
    mismatch = np.sum(np.abs(sim_exposure - target_exposure.values))
    trades = np.sum(np.diff(sim_exposure) != 0)
    
    print(f"\nOptimization results:")
    print(f"  Total mismatched days: {mismatch} days (out of {len(df)})")
    print(f"  Accuracy: {(1.0 - mismatch/len(df))*100:.2f}%")
    print(f"  Number of simulated trades (entries + exits): {trades}")
    
    # Save results
    output = {
        "params": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in best_params.items()},
        "mismatch_days": int(mismatch),
        "accuracy": float(1.0 - mismatch/len(df)),
        "trades": int(trades)
    }
    
    with open("tmp/optimize_user_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved results to tmp/optimize_user_results.json")

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
