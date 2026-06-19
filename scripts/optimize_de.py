import sqlite3
import pandas as pd
import numpy as np
from src.data.valuation_api_client import ValuationApiClient
from scipy.optimize import differential_evolution
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

df = load_data()
scores = df["score"].values
regimes = df["regime"].values
comps = df["composite_value"].values
returns = df["simple_return"].values
n = len(df)
years = n / 365.25

# Create a mapping for regimes for fast lookup
is_bear = (regimes == "BEAR")
is_bull = (regimes == "BULL")

def objective(x):
    s_enter_full, s_exit_full, comp_val_in, comp_val_out, comp_cb = x
    
    exposures = np.zeros(n)
    prev = 0.0
    for i in range(n):
        s = scores[i]
        c = comps[i]
        b = is_bear[i]
        
        exposure = prev
        
        # Base logic
        if s >= s_enter_full:
            exposure = 1.0
        elif s <= s_exit_full:
            exposure = 0.0
            
        if b:
            exposure = 0.0
            
        if c >= comp_val_in:
            exposure = max(exposure, 0.5)
            
        if c <= comp_val_out:
            # Drop to 0.5 if extremely overvalued
            exposure = min(exposure, 0.5)
            
        if c <= comp_cb:
            exposure = 0.0
            
        exposures[i] = exposure
        prev = exposure
        
    positions = np.sign(scores) * np.abs(exposures)
    strat_ret = np.roll(positions, 1) * returns
    strat_ret[0] = 0.0
    
    equity = np.cumprod(1 + strat_ret)
    
    cagr = (equity[-1] ** (1 / years) - 1) * 100
    
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = np.min(dd) * 100
    
    # We want to maximize CAGR, so we minimize -CAGR
    # Add a strong penalty if max_dd is worse than -50%
    penalty = 0
    if max_dd < -50.0:
        penalty = ((-50.0 - max_dd) ** 2) * 10
        
    return -cagr + penalty

def main():
    bounds = [
        (0.3, 0.9),     # s_enter_full
        (-0.5, 0.5),    # s_exit_full
        (0.5, 2.0),     # comp_val_in
        (-1.5, 0.0),    # comp_val_out
        (-2.5, -1.0),   # comp_cb
    ]
    
    res = differential_evolution(objective, bounds, maxiter=20, popsize=10, disp=True)
    
    print("Optimization Result:")
    print(res.x)
    print(f"Best Objective: {-res.fun:.2f}")

if __name__ == "__main__":
    main()
