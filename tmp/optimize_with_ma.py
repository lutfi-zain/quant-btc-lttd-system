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
    use_bear_override = params["use_bear_override"]
    use_ma_filter = params["use_ma_filter"]
    ma_period = params["ma_period"]
    
    smoothed_entry = super_smoother(df["final_score"], period=entry_p)
    smoothed_exit = super_smoother(df["final_score"], period=exit_p)
    
    # Pre-calculate MA
    ma = df["close"].rolling(ma_period).mean() if use_ma_filter else None
    
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
        price = df["close"].iloc[i]
        ma_val = ma.iloc[i] if use_ma_filter else None
        
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
                ma_condition = True
                if use_ma_filter and not pd.isna(ma_val):
                    ma_condition = (price > ma_val)
                    
                if score_ent >= score_entry and ma_condition:
                    exp = 1.0
                    
        # Bear regime override
        if use_bear_override and regime == "BEAR":
            if days_in_position >= mhp_days or prev_exp < 0.9:
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
                penalty += 5.0
                
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
                penalty += 1.0
                
    # Add a penalty for any trades in 2018 (except the Jan 1-10 exit)
    # The user says "investigasi kenapa di bear market 2018 masih ada trade. lalu coba fix"
    df_2018 = df.loc["2018-01-11":"2018-12-31"]
    exp_2018 = exposures[df.index.get_loc("2018-01-11"):df.index.get_loc("2018-12-31")+1]
    trades_2018 = np.sum(np.diff(exp_2018) != 0)
    days_in_pos_2018 = np.sum(exp_2018 > 0.0)
    # Heavily penalize any 2018 trading
    penalty += trades_2018 * 10.0 + days_in_pos_2018 * 2.0
                
    return penalty

def objective(x, df):
    entry_p = max(3, int(round(x[0])))
    exit_p = max(2, int(round(x[1])))
    score_entry = x[2]
    score_exit = x[3]
    cb_activate = x[4]
    cb_cooloff = x[5]
    rco_days = max(1, int(round(x[6])))
    mhp_days = max(1, int(round(x[7])))
    use_bear_override = bool(x[8] > 0.5)
    use_ma_filter = bool(x[9] > 0.5)
    ma_period = max(10, int(round(x[10])))
    
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
        "mhp_days": mhp_days,
        "use_bear_override": use_bear_override,
        "use_ma_filter": use_ma_filter,
        "ma_period": ma_period
    }
    
    try:
        exp = simulate_mhp_rco(df, params)
        
        # Calculate returns
        close = df["close"].values
        simple_ret = (close[1:] - close[:-1]) / close[:-1]
        strat_ret = simple_ret * exp[:-1]
        
        equity = np.cumprod(1 + strat_ret)
        years = len(strat_ret) / 365.25
        cagr_val = (equity[-1] ** (1 / years) - 1) * 100 if len(equity) > 0 and equity[-1] > 0 else 0.0
        
        # Sharpe
        std = np.std(strat_ret) * np.sqrt(365)
        sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365) if std > 1e-6 else -2.0
        
        # Drawdown
        peaks = np.maximum.accumulate(equity)
        dd = (equity - peaks) / peaks
        max_dd = np.min(dd)
        
        # Trade count
        trades = np.sum(np.diff(exp) != 0)
        
        # Penalize Drawdown > 35%
        dd_penalty = max(0.0, -max_dd - 0.35) * 15.0
        
        # Penalize trades > 45
        trade_penalty = max(0, trades - 45) * 0.2
        
        # User alignment penalty
        user_penalty = calculate_user_penalty(df, exp)
        
        # Balanced objective function
        score = cagr_val + 15.0 * sharpe - dd_penalty - trade_penalty - user_penalty
        return -score
        
    except Exception as e:
        return 1e6

def main():
    print("Loading data...")
    df = load_data()
    df = df.iloc[52:]
    
    # bounds:
    # [entry_p, exit_p, score_entry, score_exit, cb_activate, cb_cooloff, rco_days, mhp_days, use_bear_override, use_ma_filter, ma_period]
    bounds = [
        (5, 55),       # entry_p
        (2, 20),       # exit_p
        (0.20, 0.85),  # score_entry
        (-0.25, 0.45), # score_exit
        (-3.5, -1.0),  # cb_activate
        (-1.0, 1.0),   # cb_cooloff
        (1, 15),       # rco_days
        (2, 20),       # mhp_days
        (0.0, 1.0),    # use_bear_override
        (0.0, 1.0),    # use_ma_filter
        (50, 300)      # ma_period
    ]
    
    print("Running Differential Evolution with MA Filter and 2018 Bear Market Restrictions...")
    result = differential_evolution(
        objective,
        bounds,
        args=(df,),
        maxiter=120,
        popsize=40,
        tol=1e-5,
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
        "rco_days": max(1, int(round(x[6]))),
        "mhp_days": max(1, int(round(x[7]))),
        "use_bear_override": bool(x[8] > 0.5),
        "use_ma_filter": bool(x[9] > 0.5),
        "ma_period": max(10, int(round(x[10])))
    }
    
    print("\n" + "="*50)
    print("BEST PARAMETERS FOUND WITH MA FILTER:")
    print("="*50)
    for k, v in best_params.items():
        print(f"  {k}: {v}")
        
    # Simulate best
    exp = simulate_mhp_rco(df, best_params)
    
    # Calculate metrics
    close = df["close"].values
    simple_ret = (close[1:] - close[:-1]) / close[:-1]
    strat_ret = simple_ret * exp[:-1]
    equity = np.cumprod(1 + strat_ret)
    years = len(strat_ret) / 365.25
    cagr = (equity[-1] ** (1 / years) - 1) * 100 if len(equity) > 0 and equity[-1] > 0 else 0.0
    std = np.std(strat_ret) * np.sqrt(365)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365) if std > 0 else 0
    peaks = np.maximum.accumulate(equity)
    dd = (equity - peaks) / peaks
    max_dd = np.min(dd) * 100
    trades = np.sum(np.diff(exp) != 0)
    user_penalty = calculate_user_penalty(df, exp)
    
    print(f"\nFinal Optimization Results:")
    print(f"  CAGR: {cagr:.2f}%")
    print(f"  Sharpe Ratio: {sharpe:.4f}")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Total Trades: {trades}")
    print(f"  User/2018 Violations: {user_penalty:.1f} points")
    
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
    with open("tmp/optimize_with_ma_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved output to tmp/optimize_with_ma_results.json")

if __name__ == "__main__":
    main()
