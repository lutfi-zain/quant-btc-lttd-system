import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import sqlite3
import pandas as pd
import numpy as np
from scipy.optimize import differential_evolution
import json

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, o.high, o.low, o.close
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
    target.loc["2017-07-29":"2018-01-10"] = 1.0
    target.loc["2020-01-10":"2020-03-04"] = 1.0
    target.loc["2020-03-16":"2021-04-27"] = 1.0
    target.loc["2021-07-23":"2021-11-28"] = 1.0
    target.loc["2023-10-22":"2024-04-15"] = 1.0
    target.loc["2024-10-01":"2025-02-15"] = 1.0
    target.loc["2025-04-20":"2025-10-23"] = 1.0
    target.loc["2018-12-20":"2019-03-01"] = 0.0
    target.loc["2017-09-22"] = 1.0
    target.loc["2018-01-09":"2018-01-11"] = 0.0
    return target

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

def simulate_supersmoother(df, params):
    entry_p = params["entry_p"]
    exit_p = params["exit_p"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    rco_days = params["rco_days"]
    
    smoothed_entry = super_smoother(df["final_score"], period=entry_p)
    smoothed_exit = super_smoother(df["final_score"], period=exit_p)
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    days_since_exit = 999
    
    for i in range(len(df)):
        score_ent = smoothed_entry.iloc[i]
        score_ex = smoothed_exit.iloc[i]
        comp = df["composite_value"].iloc[i]
        regime = df["regime"].iloc[i]
        
        exp = prev_exp
        
        if prev_exp >= 0.9:
            days_since_exit = 0
        else:
            days_since_exit += 1
            
        # Circuit Breaker
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
                
        # Score based entry/exit
        if prev_exp >= 0.9:
            if score_ex <= score_exit:
                exp = 0.0
        else:
            # Re-entry cooloff
            if days_since_exit >= rco_days:
                if score_ent >= score_entry:
                    exp = 1.0
                    
        # Bear regime override
        if regime == "BEAR":
            exp = 0.0
            
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

def objective(x, df, target):
    entry_p = max(3, int(round(x[0])))
    exit_p = max(2, int(round(x[1])))
    score_entry = x[2]
    score_exit = x[3]
    cb_activate = x[4]
    cb_cooloff = x[5]
    rco_days = max(0, int(round(x[6])))
    
    if entry_p < exit_p:
        return 1e6
    if score_entry <= score_exit:
        return 1e6
    if cb_cooloff <= cb_activate:
        return 1e6
        
    params = {
        "entry_p": entry_p,
        "exit_p": exit_p,
        "score_entry": score_entry,
        "score_exit": score_exit,
        "cb_activate": cb_activate,
        "cb_cooloff": cb_cooloff,
        "rco_days": rco_days
    }
    
    try:
        exp = simulate_supersmoother(df, params)
        
        # Calculate metrics
        close = df["close"].values
        log_ret = np.log(close[1:] / close[:-1])
        strat_ret = log_ret * exp[:-1]
        
        # Sharpe
        std = np.std(strat_ret) * np.sqrt(365.25)
        sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365.25) if std > 1e-6 else -2.0
        
        # Drawdown
        cum_ret = np.exp(np.cumsum(strat_ret))
        peaks = np.maximum.accumulate(cum_ret)
        dd = (cum_ret - peaks) / peaks
        max_dd = np.min(dd)
        
        # Mismatch
        mis = np.sum(exp != target.values)
        mismatch_ratio = mis / len(df)
        
        # Penalties
        dd_penalty = max(0.0, -max_dd - 0.40) * 10.0  # Penalize Drawdown > 40%
        
        # We want to maximize Sharpe + (1 - mismatch_ratio) * 1.5
        # So objective = - (Sharpe + (1 - mismatch_ratio) * 1.5) + dd_penalty
        score = sharpe + (1.0 - mismatch_ratio) * 2.0 - dd_penalty
        return -score
        
    except Exception:
        return 1e6

def calculate_metrics(df, exposures):
    close = df["close"].values
    log_ret = np.log(close[1:] / close[:-1])
    strat_ret = log_ret * exposures[:-1]
    
    cagr = (np.exp(np.sum(strat_ret)) ** (365.25 / len(strat_ret)) - 1) * 100
    std = np.std(strat_ret) * np.sqrt(365.25)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365.25) if std > 0 else 0
    
    cum_ret = np.exp(np.cumsum(strat_ret))
    peaks = np.maximum.accumulate(cum_ret)
    dd = (cum_ret - peaks) / peaks
    max_dd = np.min(dd) * 100
    
    trades = np.sum(np.diff(exposures) != 0)
    
    return cagr, sharpe, max_dd, trades

def main():
    print("Loading data...")
    df = load_data()
    # Warmup
    df = df.iloc[52:]
    target = get_user_target_exposure(df.index)
    
    # bounds:
    # [entry_p, exit_p, score_entry, score_exit, cb_activate, cb_cooloff, rco_days]
    bounds = [
        (5, 40),       # entry_p
        (2, 20),       # exit_p
        (0.20, 0.85),  # score_entry
        (-0.20, 0.50), # score_exit
        (-3.0, -0.5),  # cb_activate
        (-0.5, 1.0),   # cb_cooloff
        (0, 15)        # rco_days
    ]
    
    print("Optimizing parameters with SuperSmoother filter...")
    result = differential_evolution(
        objective,
        bounds,
        args=(df, target),
        maxiter=100,
        popsize=30,
        tol=1e-6,
        seed=42,
        disp=True,
        workers=1
    )
    
    x = result.x
    best_params = {
        "entry_p": max(3, int(round(x[0]))),
        "exit_p": max(2, int(round(x[1]))),
        "score_entry": float(x[2]),
        "score_exit": float(x[3]),
        "cb_activate": float(x[4]),
        "cb_cooloff": float(x[5]),
        "rco_days": max(0, int(round(x[6])))
    }
    
    print("\n" + "="*50)
    print("BEST SUPERSMOOTHER PARAMETERS:")
    print("="*50)
    for k, v in best_params.items():
        print(f"  {k}: {v}")
        
    # Simulate best
    exp = simulate_supersmoother(df, best_params)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp)
    mis = np.sum(exp != target.values)
    
    print(f"\nFinal Results:")
    print(f"  CAGR: {cagr:.2f}%")
    print(f"  Sharpe Ratio: {sharpe:.4f}")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Total Trades: {trades}")
    print(f"  Mismatch Days: {mis} out of {len(df)} ({(1 - mis/len(df))*100:.2f}% Accuracy)")
    
    # Save
    output = {
        "params": best_params,
        "metrics": {
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "trades": int(trades),
            "mismatch_days": int(mis),
            "accuracy": float(1 - mis/len(df))
        }
    }
    with open("tmp/optimize_supersmoother_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved output to tmp/optimize_supersmoother_results.json")

if __name__ == "__main__":
    main()
