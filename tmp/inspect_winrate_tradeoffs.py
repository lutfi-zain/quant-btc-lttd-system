#!/usr/bin/env python3
import sqlite3
import numpy as np
import pandas as pd
import json
import os
import sys

# Ensure parent directory is in Python path for importing ValuationApiClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    df["simple_return"] = df["close"].pct_change().fillna(0.0)
    
    # Load composite values
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

def precompute_caches(df):
    entry_cache = {}
    for p in range(3, 30):
        entry_cache[p] = super_smoother(df["final_score"], p).values

    exit_cache = {}
    for p in range(2, 20):
        exit_cache[p] = super_smoother(df["final_score"], p).values

    ma_cache = {}
    for p in range(50, 300):
        ma_cache[p] = df["close"].rolling(p).mean().values
        
    return entry_cache, exit_cache, ma_cache

def simulate_exposures_fast(df, params, entry_cache, exit_cache, ma_cache):
    entry_p = int(round(params["entry_p"]))
    exit_p = int(round(params["exit_p"]))
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    rco_days = int(round(params["rco_days"]))
    mhp_days = int(round(params["mhp_days"]))
    use_bear_override = params["use_bear_override"]
    use_ma_filter = params["use_ma_filter"]
    ma_period = int(round(params["ma_period"]))
    
    smoothed_entry = entry_cache[entry_p]
    smoothed_exit = exit_cache[exit_p]
    ma_val_arr = ma_cache[ma_period] if use_ma_filter else None
    
    close_val = df["close"].values
    regime_val = df["regime"].values
    comp_val = df["composite_value"].values
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    days_since_exit = 999
    days_in_position = 0
    
    for i in range(len(df)):
        score_ent = smoothed_entry[i]
        score_ex = smoothed_exit[i]
        comp = comp_val[i]
        regime = regime_val[i]
        price = close_val[i]
        ma_val = ma_val_arr[i] if ma_val_arr is not None else None
        
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
                if use_ma_filter and ma_val is not None and not np.isnan(ma_val):
                    ma_condition = (price > ma_val)
                    
                if score_ent >= score_entry and ma_condition:
                    exp = 1.0
            
        # BEAR regime override
        if use_bear_override and regime == "BEAR":
            exp = 0.0
            
        # Deep value boost override
        if comp >= 2.000613 and exp == 0.0:
            if days_since_exit >= rco_days:
                exp = 1.0
            
        # Binary enforcement
        exp = 1.0 if exp > 0.5 else 0.0
        
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

def calculate_metrics_vectorized(df, exposures):
    close = df["close"].values
    btcDailyReturn = (close[1:] - close[:-1]) / close[:-1]
    stratReturn = exposures[:-1] * btcDailyReturn
    
    equity_curve = np.cumprod(1.0 + stratReturn)
    equity = equity_curve[-1]
    peakEquity = np.maximum.accumulate(equity_curve)
    maxDrawdown = np.max((peakEquity - equity_curve) / peakEquity)
    
    days = len(stratReturn)
    years = days / 365.25
    
    totalReturnPct = (equity - 1.0) * 100.0
    cagr = (equity ** (1.0 / years) - 1.0) * 100.0 if equity > 0 else 0.0
    
    meanDailyReturn = np.mean(stratReturn)
    stdDev = np.std(stratReturn)
    annualizedStdDev = stdDev * np.sqrt(365)
    
    negativeReturns = stratReturn[stratReturn < 0.0]
    downsideDev = np.sqrt(np.sum(negativeReturns ** 2) / days) if len(negativeReturns) > 0 else 0.0
    annualizedDownsideDev = downsideDev * np.sqrt(365)
    
    sharpe = (meanDailyReturn * 365.0) / annualizedStdDev if annualizedStdDev > 0 else 0.0
    sortino = (meanDailyReturn * 365.0) / annualizedDownsideDev if annualizedDownsideDev > 0 else 0.0
    
    entries = (exposures[1:] > 0.0) & (exposures[:-1] == 0.0)
    exits = (exposures[1:] == 0.0) & (exposures[:-1] > 0.0)
    
    entry_indices = np.where(entries)[0] + 1
    exit_indices = np.where(exits)[0] + 1
    
    if exposures[0] > 0.0:
        entry_indices = np.insert(entry_indices, 0, 0)
        
    num_entries = len(entry_indices)
    num_exits = len(exit_indices)
    
    totalTrades = num_entries
    winTrades = 0
    
    for k in range(min(num_entries, num_exits)):
        e_idx = entry_indices[k]
        ex_idx = exit_indices[k]
        tr = np.prod(1.0 + stratReturn[e_idx : ex_idx]) - 1.0
        if tr > 0.0:
            winTrades += 1
            
    winRate = (winTrades / totalTrades) * 100.0 if totalTrades > 0 else 0.0
    
    return {
        "strategy_return": totalReturnPct,
        "cagr": cagr,
        "max_dd": maxDrawdown * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": winRate,
        "total_trades": totalTrades,
        "win_trades": winTrades
    }

def main():
    df = load_data()
    df = df.iloc[1:]
    entry_cache, exit_cache, ma_cache = precompute_caches(df)
    
    print("Running random search for tradeoffs analysis...")
    results = []
    
    np.random.seed(42)
    for iteration in range(25000):
        params = {
            "entry_p": int(np.random.randint(4, 25)),
            "exit_p": int(np.random.randint(2, 15)),
            "score_entry": float(np.random.uniform(0.30, 0.65)),
            "score_exit": float(np.random.uniform(0.15, 0.45)),
            "cb_activate": float(np.random.uniform(-3.5, -2.0)),
            "cb_cooloff": float(np.random.uniform(0.5, 1.2)),
            "rco_days": int(np.random.randint(1, 8)),
            "mhp_days": int(np.random.randint(5, 20)),
            "use_bear_override": bool(np.random.choice([True, False])),
            "use_ma_filter": True,
            "ma_period": int(np.random.randint(150, 300))
        }
        
        if params["entry_p"] <= params["exit_p"]:
            continue
        if params["score_entry"] <= params["score_exit"]:
            continue
        if params["cb_cooloff"] <= params["cb_activate"]:
            continue
            
        test_exps = simulate_exposures_fast(df, params, entry_cache, exit_cache, ma_cache)
        metrics = calculate_metrics_vectorized(df, test_exps)
        
        results.append((params, metrics))
        
    print("\n--- TOP 20 HIGHEST WIN RATES ---")
    results.sort(key=lambda x: x[1]["win_rate"], reverse=True)
    for idx, (p, m) in enumerate(results[:20]):
        print(f"#{idx+1:02d}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:,.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Trades={m['total_trades']}")
        
    print("\n--- TOP 20 BY win_rate >= 70% SORTED BY cagr DESC ---")
    cands_70 = [r for r in results if r[1]["win_rate"] >= 70.0]
    cands_70.sort(key=lambda x: x[1]["cagr"], reverse=True)
    for idx, (p, m) in enumerate(cands_70[:20]):
        print(f"#{idx+1:02d}: WinRate={m['win_rate']:.2f}% | Return={m['strategy_return']:,.2f}% | MaxDD={m['max_dd']:.2f}% | Sharpe={m['sharpe']:.2f} | Trades={m['total_trades']}")
        print(f"      Params: entry_p={p['entry_p']}, exit_p={p['exit_p']}, score_entry={p['score_entry']:.3f}, score_exit={p['score_exit']:.3f}, cb_act={p['cb_activate']:.2f}, cb_cool={p['cb_cooloff']:.2f}, rco={p['rco_days']}, mhp={p['mhp_days']}, bear={p['use_bear_override']}, ma={p['ma_period']}")

if __name__ == "__main__":
    main()
