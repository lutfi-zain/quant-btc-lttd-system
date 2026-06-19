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

def simulate_mhp_rco(df, params):
    entry_p = params["entry_p"]
    exit_p = params["exit_p"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    rco_days = params["rco_days"]
    mhp_days = params["mhp_days"]
    
    smoothed_entry = super_smoother(df["final_score"], period=entry_p)
    smoothed_exit = super_smoother(df["final_score"], period=exit_p)
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    days_since_exit = 999
    days_in_position = 0
    
    for i in range(len(df)):
        score_ent = smoothed_entry.iloc[i]
        score_ex = smoothed_exit.iloc[i]
        comp = df["composite_value"].iloc[i]
        regime = df["regime"].iloc[i]
        
        # Increment timers
        if prev_exp >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
        exp = prev_exp
        
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
        if prev_exp >= 0.9:  # IN position
            if days_in_position < mhp_days:
                exp = 1.0  # Force hold (MHP)
            else:
                if score_ex <= score_exit:
                    exp = 0.0
        else:  # OUT position
            if days_since_exit >= rco_days:
                if score_ent >= score_entry:
                    exp = 1.0
                    
        # Bear regime override
        if regime == "BEAR":
            exp = 0.0
            
        # Deep value boost override
        if comp >= 2.000613 and exp == 0.0:
            if days_since_exit >= rco_days:
                exp = 1.0
            
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

def calculate_user_penalty(df, exposures):
    penalty = 0.0
    
    # Specific date rules: (date_str, expected_exposure)
    rules = [
        ("2016-01-26", 0.0),
        ("2016-08-09", 0.0),
        ("2017-01-28", 0.0),
        ("2017-07-14", 0.0),
        ("2017-09-25", 0.0),
        ("2018-01-16", 0.0),
        ("2018-08-18", 0.0),
        ("2019-04-09", 1.0),
        ("2019-07-30", 0.0),
        ("2020-03-10", 0.0),
        ("2020-05-23", 1.0),
        ("2021-09-18", 0.0),
        ("2021-09-25", 0.0),
        ("2021-11-30", 0.0),
        ("2023-08-01", 0.0),
    ]
    
    for date_str, expected in rules:
        ts = pd.Timestamp(date_str)
        if ts in df.index:
            idx = df.index.get_loc(ts)
            if exposures[idx] != expected:
                penalty += 15.0  # Heavy penalty for violating single dates
                
    # Range rules: (start_date, end_date, expected_exposure)
    ranges = [
        ("2020-02-16", "2020-03-03", 1.0),
        ("2022-04-08", "2022-04-15", 0.0),
        ("2023-03-13", "2023-03-15", 1.0),
    ]
    
    for start_str, end_str, expected in ranges:
        mask = (df.index >= pd.Timestamp(start_str)) & (df.index <= pd.Timestamp(end_str))
        indices = np.where(mask)[0]
        for idx in indices:
            if exposures[idx] != expected:
                penalty += 5.0  # Penalty per day of violation in ranges
                
    return penalty

def objective(x, df):
    entry_p = max(3, int(round(x[0])))
    exit_p = max(2, int(round(x[1])))
    score_entry = x[2]
    score_exit = x[3]
    cb_activate = x[4]
    cb_cooloff = x[5]
    rco_days = max(0, int(round(x[6])))
    mhp_days = max(0, int(round(x[7])))
    
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
        "rco_days": rco_days,
        "mhp_days": mhp_days
    }
    
    try:
        exp = simulate_mhp_rco(df, params)
        
        # Calculate metrics (365 trading days)
        close = df["close"].values
        simple_ret = (close[1:] - close[:-1]) / close[:-1]
        strat_ret = simple_ret * exp[:-1]
        
        # Sharpe (using 365 days)
        std = np.std(strat_ret) * np.sqrt(365)
        sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365) if std > 1e-6 else -2.0
        
        # Drawdown
        cum_ret = np.cumprod(1 + strat_ret)
        peaks = np.maximum.accumulate(cum_ret)
        dd = (cum_ret - peaks) / peaks
        max_dd = np.min(dd)
        
        # Trade count penalty
        trades = np.sum(np.diff(exp) != 0)
        trade_penalty = max(0, trades - 70) * 0.1  # penalize too many trades
        
        # Drawdown penalty
        dd_penalty = max(0.0, -max_dd - 0.40) * 20.0  # Penalize Drawdown > 40%
        
        # User alignment penalty
        user_penalty = calculate_user_penalty(df, exp)
        
        # Objective function
        # Maximize Sharpe while minimizing user penalty, trades, and drawdown
        score = sharpe - dd_penalty - trade_penalty - user_penalty
        return -score
        
    except Exception as e:
        return 1e6

def calculate_metrics(df, exposures):
    close = df["close"].values
    simple_ret = (close[1:] - close[:-1]) / close[:-1]
    strat_ret = simple_ret * exposures[:-1]
    
    equity = np.cumprod(1 + strat_ret)
    total_ret = (equity[-1] - 1) * 100 if len(equity) > 0 else 0.0
    
    years = len(strat_ret) / 365.25
    cagr = (Math_pow_safe(equity[-1], 1 / years) - 1) * 100 if len(equity) > 0 else 0.0
    
    std = np.std(strat_ret) * np.sqrt(365)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365) if std > 0 else 0
    
    peaks = np.maximum.accumulate(equity)
    dd = (equity - peaks) / peaks
    max_dd = np.min(dd) * 100
    
    trades = np.sum(np.diff(exposures) != 0)
    
    return cagr, sharpe, max_dd, trades

def Math_pow_safe(base, exp):
    if base <= 0:
        return 0.0
    return Math.pow(base, exp)

import math as Math

def main():
    print("Loading data...")
    df = load_data()
    # Warmup
    df = df.iloc[52:]
    
    # bounds:
    # [entry_p, exit_p, score_entry, score_exit, cb_activate, cb_cooloff, rco_days, mhp_days]
    bounds = [
        (10, 60),      # entry_p
        (3, 25),       # exit_p
        (0.20, 0.85),  # score_entry
        (-0.20, 0.50), # score_exit
        (-3.0, -0.5),  # cb_activate
        (-0.5, 1.0),   # cb_cooloff
        (2, 20),       # rco_days
        (2, 20)        # mhp_days
    ]
    
    print("Optimizing parameters with SuperSmoother + RCO + MHP + User Constraints...")
    result = differential_evolution(
        objective,
        bounds,
        args=(df,),
        maxiter=150,
        popsize=40,
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
        "rco_days": max(0, int(round(x[6]))),
        "mhp_days": max(0, int(round(x[7])))
    }
    
    print("\n" + "="*50)
    print("BEST PARAMETERS FOUND:")
    print("="*50)
    for k, v in best_params.items():
        print(f"  {k}: {v}")
        
    # Simulate best
    exp = simulate_mhp_rco(df, best_params)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp)
    user_penalty = calculate_user_penalty(df, exp)
    
    print(f"\nFinal Results:")
    print(f"  CAGR: {cagr:.2f}%")
    print(f"  Sharpe Ratio: {sharpe:.4f}")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Total Trades: {trades}")
    print(f"  User Penalty Violations: {user_penalty / 5.0:.1f} days equivalent")
    
    # Save
    output = {
        "params": best_params,
        "metrics": {
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "trades": int(trades),
            "user_penalty": float(user_penalty)
        }
    }
    with open("tmp/optimize_mhp_rco_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved output to tmp/optimize_mhp_rco_results.json")

if __name__ == "__main__":
    main()
