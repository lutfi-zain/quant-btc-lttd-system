import sqlite3
import pandas as pd
import numpy as np
from src.data.valuation_api_client import ValuationApiClient
from itertools import product
from multiprocessing import Pool
import os

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score as score, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df["simple_return"] = df["close"].pct_change().fillna(0.0)
    
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is not None:
        val_df["date"] = pd.to_datetime(val_df["date"]).dt.tz_convert(None)
        val_df.set_index("date", inplace=True)
        df = df.join(val_df, how="left")
        
    df["composite_value"] = df["composite_value"].fillna(0.0)
    return df

def run_sim(args):
    df, s_enter_full, s_exit_part, s_exit_full, comp_val_in, comp_val_out, comp_cb = args
    
    # Pre-allocate array for speed
    n = len(df)
    exposures = np.zeros(n)
    
    scores = df["score"].values
    regimes = df["regime"].values
    comps = df["composite_value"].values
    
    prev = 0.0
    for i in range(n):
        s = scores[i]
        r = regimes[i]
        c = comps[i]
        
        exposure = prev
        
        # Base logic
        if s >= s_enter_full:
            exposure = 1.0
        elif s <= s_exit_full:
            exposure = 0.0
        
        # Bear
        if r == "BEAR":
            exposure = 0.0
            
        # Value Scaling In
        if c >= comp_val_in:
            exposure = max(exposure, 0.5)
            
        # Value Scaling Out
        if c <= comp_val_out:
            if s < s_exit_part: # If momentum dropping
                exposure = 0.0
            else:
                exposure = min(exposure, 0.5)
                
        # Circuit Breaker
        if c <= comp_cb:
            exposure = 0.0
            
        exposures[i] = exposure
        prev = exposure
        
    # Vectorized compute
    positions = np.sign(scores) * np.abs(exposures)
    strat_ret = np.roll(positions, 1) * df["simple_return"].values
    strat_ret[0] = 0.0
    
    equity = np.cumprod(1 + strat_ret)
    total_ret = equity[-1] - 1
    
    years = n / 365.25
    cagr = (equity[-1] ** (1 / years) - 1) * 100
    
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = np.min(dd) * 100
    
    return (s_enter_full, s_exit_part, s_exit_full, comp_val_in, comp_val_out, comp_cb, cagr, max_dd)

def main():
    df = load_data()
    
    # Search space
    s_enter_full_vals = [0.4, 0.5, 0.6, 0.65]
    s_exit_part_vals = [0.7, 0.8, 0.85]
    s_exit_full_vals = [0.1, 0.2, 0.3]
    comp_val_in_vals = [0.8, 1.0, 1.2, 1.5]
    comp_val_out_vals = [-0.8, -1.0, -1.2]
    comp_cb_vals = [-1.5, -1.8, -2.0]
    
    params = list(product(
        s_enter_full_vals,
        s_exit_part_vals,
        s_exit_full_vals,
        comp_val_in_vals,
        comp_val_out_vals,
        comp_cb_vals
    ))
    
    print(f"Total combinations: {len(params)}")
    
    best_cagr = 0
    best_params = None
    best_dd = 0
    
    for p in params:
        args = (df, *p)
        res = run_sim(args)
        if res[6] > best_cagr and res[7] > -70.0: # Filter Max DD < -70%
            best_cagr = res[6]
            best_dd = res[7]
            best_params = p
            print(f"New Best! CAGR: {best_cagr:.2f}%, Max DD: {best_dd:.2f}%, Params: {best_params}")

if __name__ == "__main__":
    main()
