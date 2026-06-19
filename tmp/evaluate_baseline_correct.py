#!/usr/bin/env python3
import sqlite3
import numpy as np
import pandas as pd
import json
import os
import sys

# Ensure parent directory is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    
    # Load all ohlcv starting from 2014 to calculate MA correctly
    ohlcv_df = pd.read_sql("""
        SELECT DATE(timestamp) as date, close
        FROM ohlcv
        ORDER BY timestamp
    """, conn, parse_dates=["date"])
    ohlcv_df.set_index("date", inplace=True)
    
    # Load daily_lttd starting from 2016
    df = pd.read_sql("""
        SELECT date, regime, final_score
        FROM daily_lttd
        ORDER BY date
    """, conn, parse_dates=["date"])
    conn.close()
    
    df.set_index("date", inplace=True)
    df = df.join(ohlcv_df[["close"]], how="inner")
    df["simple_return"] = df["close"].pct_change()
    
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
    
    return df, ohlcv_df

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

def precompute_caches(df, ohlcv_df):
    entry_cache = {}
    for p in range(3, 30):
        entry_cache[p] = super_smoother(df["final_score"], p).values

    exit_cache = {}
    for p in range(2, 20):
        exit_cache[p] = super_smoother(df["final_score"], p).values

    ma_cache = {}
    for p in range(50, 300):
        ma_full = ohlcv_df["close"].rolling(p).mean()
        ma_cache[p] = df.join(ma_full.to_frame("ma"), how="left")["ma"].values
        
    return entry_cache, exit_cache, ma_cache

def simulate_exposures(df, params, entry_cache, exit_cache, ma_cache):
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

def calculate_metrics_react(df, exposures):
    close = df["close"].values
    
    equity = 1.0
    btcHold = 1.0
    peakEquity = 1.0
    maxDrawdown = 0.0
    
    prevExposure = 0.0
    dailyReturns = []
    
    winTrades = 0
    totalTrades = 0
    currentTradeReturn = 0.0
    inTrade = False
    
    for i in range(len(df)):
        if i > 0:
            prev_close = close[i-1]
            price = close[i]
            btcDailyReturn = (price - prev_close) / prev_close
            btcHold = btcHold * (1.0 + btcDailyReturn)
            
            stratReturn = prevExposure * btcDailyReturn
            equity = equity * (1.0 + stratReturn)
            dailyReturns.push(stratReturn) if hasattr(dailyReturns, "push") else dailyReturns.append(stratReturn)
            
            if equity > peakEquity:
                peakEquity = equity
            drawdown = (peakEquity - equity) / peakEquity
            if drawdown > maxDrawdown:
                maxDrawdown = drawdown
                
            if inTrade:
                currentTradeReturn = (1.0 + currentTradeReturn) * (1.0 + stratReturn) - 1.0
                
        exposure = exposures[i]
        if exposure > 0.0 and prevExposure == 0.0:
            inTrade = True
            currentTradeReturn = 0.0
            totalTrades += 1
        elif exposure == 0.0 and prevExposure > 0.0:
            inTrade = False
            if currentTradeReturn > 0.0:
                winTrades += 1
                
        prevExposure = exposure
        
    days = len(dailyReturns)
    years = days / 365.25
    
    totalReturnPct = (equity - 1.0) * 100.0
    btcReturnPct = (btcHold - 1.0) * 100.0
    
    cagr = (equity ** (1.0 / (years or 1.0)) - 1.0) * 100.0 if equity > 0 else 0.0
    btcCagr = (btcHold ** (1.0 / (years or 1.0)) - 1.0) * 100.0 if btcHold > 0 else 0.0
    
    meanDailyReturn = sum(dailyReturns) / (days or 1)
    variance = sum((r - meanDailyReturn) ** 2 for r in dailyReturns) / (days or 1)
    stdDev = np.sqrt(variance)
    annualizedStdDev = stdDev * np.sqrt(365)
    
    negativeReturns = [r for r in dailyReturns if r < 0.0]
    downsideVariance = sum(r ** 2 for r in negativeReturns) / (days or 1) if negativeReturns else 0.0
    annualizedDownsideDev = np.sqrt(downsideVariance) * np.sqrt(365)
    
    sharpe = (meanDailyReturn * 365.0) / annualizedStdDev if annualizedStdDev > 0 else 0.0
    sortino = (meanDailyReturn * 365.0) / annualizedDownsideDev if annualizedDownsideDev > 0 else 0.0
    winRate = (winTrades / totalTrades) * 100.0 if totalTrades > 0 else 0.0
    
    return {
        "strategy_return": totalReturnPct,
        "btc_return": btcReturnPct,
        "cagr": cagr,
        "btc_cagr": btcCagr,
        "max_dd": maxDrawdown * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": winRate,
        "total_trades": totalTrades,
        "win_trades": winTrades
    }

def main():
    df, ohlcv_df = load_data()
    
    # Load actual database exposures for validation
    conn = sqlite3.connect("database/lttd.db")
    db_df = pd.read_sql("SELECT date, target_exposure FROM daily_lttd ORDER BY date", conn, parse_dates=["date"])
    conn.close()
    db_df.set_index("date", inplace=True)
    
    db_exposures = df.join(db_df, how="left")["target_exposure"].fillna(0.0).values
    
    metrics = calculate_metrics_react(df, db_exposures)
    
    print("\n--- BASELINE PARAMETERS METRICS (DATABASE EXPOSURES) ---")
    for k, v in metrics.items():
        print(f"  {k:16}: {v:.4f}" if isinstance(v, float) else f"  {k:16}: {v}")
        
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
    
    entry_cache, exit_cache, ma_cache = precompute_caches(df, ohlcv_df)
    sim_exps = simulate_exposures(df, baseline_params, entry_cache, exit_cache, ma_cache)
    
    # Compare exposures
    diff = np.where(sim_exps != db_exposures)[0]
    print(f"\nNumber of differences between simulated and database exposures: {len(diff)}")
    if len(diff) > 0:
        print("First 10 differences:")
        for idx in diff[:10]:
            print(f"  Date: {df.index[idx].strftime('%Y-%m-%d')} | Sim: {sim_exps[idx]} | DB: {db_exposures[idx]}")
            
    sim_metrics = calculate_metrics_react(df, sim_exps)
    print("\n--- BASELINE PARAMETERS METRICS (SIMULATED EXPOSURES) ---")
    for k, v in sim_metrics.items():
        print(f"  {k:16}: {v:.4f}" if isinstance(v, float) else f"  {k:16}: {v}")

if __name__ == "__main__":
    main()
