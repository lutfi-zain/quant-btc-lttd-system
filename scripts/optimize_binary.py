#!/usr/bin/env python3
"""
Binary Sizing Optimizer — Strict 0% / 100% Exposure
Uses Differential Evolution to find optimal thresholds for:
  - Score entry/exit with hysteresis
  - Composite value circuit breaker with cool-off
  - BEAR regime handling
  - EMA smoothing span
  
Objective: maximize risk-adjusted returns (composite of CAGR, Sharpe, DrawDown)
"""

import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

# ─── Load Data ──────────────────────────────────────────────────────

def load_data():
    """Load daily_lttd + ohlcv + composite values."""
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
    
    # Load composite values from valuation API cache
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    # Trigger cache load
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

# ─── Simulation Engine ──────────────────────────────────────────────

def simulate_binary(df, params, return_series=False):
    """
    Simulate strict binary (0/100%) strategy.
    
    params dict keys:
      - ema_span_entry: EMA smoothing span for entry trigger
      - ema_span_exit: EMA smoothing span for exit trigger
      - score_entry: score threshold to enter (go to 100%)
      - score_exit: score threshold to exit (go to 0%)
      - use_bear_override: if True, BEAR regime forces 0%
      - cb_activate: composite_value <= this activates circuit breaker
      - cb_cooloff: composite_value > this deactivates circuit breaker
      - comp_entry_boost: composite_value >= this forces entry even if score is below threshold
    """
    ema_entry = params["ema_span_entry"]
    ema_exit = params["ema_span_exit"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    use_bear = params["use_bear_override"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    comp_entry_boost = params.get("comp_entry_boost", 99.0)
    
    # Apply asymmetric EMA smoothing
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
        
        # Circuit breaker logic (hysteresis)
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
        
        # Score-based entry/exit with hysteresis
        if prev_exp >= 0.9:  # currently IN (use exit score)
            if score_ex <= score_exit:
                exp = 0.0
        else:  # currently OUT (use entry score)
            if score_ent >= score_entry:
                exp = 1.0
        
        # BEAR regime override
        if use_bear and regime == "BEAR":
            exp = 0.0
            
        # Composite value entry boost (deeply undervalued → enter even if score weak)
        if comp >= comp_entry_boost and exp == 0.0:
            exp = 1.0
        
        exposures[i] = exp
        prev_exp = exp
    
    # Calculate returns
    positions = exposures
    strat_returns = np.zeros(len(df))
    strat_returns[1:] = positions[:-1] * df["simple_return"].values[1:]
    
    equity = np.cumprod(1.0 + strat_returns)
    
    if return_series:
        return equity, exposures, strat_returns
    
    return equity, strat_returns

def calc_metrics(equity, strat_returns, df):
    """Calculate all performance metrics from equity curve."""
    years = (df.index[-1] - df.index[0]).days / 365.25
    if years <= 0 or equity[-1] <= 0:
        return None
    
    cagr = (equity[-1] ** (1 / years) - 1) * 100
    
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = np.min(dd) * 100
    
    sr = strat_returns
    if np.std(sr) == 0:
        sharpe = 0.0
    else:
        sharpe = np.sqrt(252) * np.mean(sr) / np.std(sr)
    
    downside = sr[sr < 0]
    if len(downside) < 5 or np.std(downside) == 0:
        sortino = 0.0
    else:
        sortino = np.sqrt(252) * np.mean(sr) / np.std(downside)
    
    # Count trades
    exp_diff = np.diff(np.concatenate([[0], np.abs(np.sign(strat_returns))]))
    
    # Trade-level stats
    in_trade = np.abs(np.sign(strat_returns)) > 0
    trade_starts = []
    trade_ends = []
    for i in range(1, len(in_trade)):
        if in_trade[i] and not in_trade[i-1]:
            trade_starts.append(i)
        if not in_trade[i] and in_trade[i-1]:
            trade_ends.append(i)
    if len(trade_starts) > len(trade_ends):
        trade_ends.append(len(in_trade) - 1)
    
    trades = []
    for s, e in zip(trade_starts, trade_ends):
        tr = np.sum(strat_returns[s:e+1])
        trades.append(tr)
    
    n_trades = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    win_rate = len(wins) / n_trades * 100 if n_trades > 0 else 0
    pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float("inf")
    
    # Buy & Hold
    bh_return = df["close"].iloc[-1] / df["close"].iloc[0]
    bh_cagr = (bh_return ** (1 / years) - 1) * 100
    
    return {
        "cagr": cagr,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": cagr / abs(max_dd) if max_dd != 0 else 0,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "profit_factor": pf,
        "total_return": (equity[-1] - 1) * 100,
        "bh_cagr": bh_cagr,
        "bh_return": (bh_return - 1) * 100,
    }

# ─── Objective Function ────────────────────────────────────────────

def objective(x, df):
    """
    Objective to minimize (negative of reward).
    x = [ema_span_entry, ema_span_exit, score_entry, score_exit, cb_activate, cb_cooloff, comp_entry_boost, use_bear_float]
    """
    ema_span_entry = max(2, int(round(x[0])))
    ema_span_exit = max(2, int(round(x[1])))
    score_entry = x[2]
    score_exit = x[3]
    cb_activate = x[4]
    cb_cooloff = x[5]
    comp_entry_boost = x[6]
    use_bear = x[7] > 0.5
    
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
        "comp_entry_boost": comp_entry_boost,
    }
    
    try:
        equity, strat_returns = simulate_binary(df, params)
        metrics = calc_metrics(equity, strat_returns, df)
        
        if metrics is None:
            return 1e6
        
        cagr = metrics["cagr"]
        max_dd = abs(metrics["max_dd"])
        sharpe = metrics["sharpe"]
        sortino = metrics["sortino"]
        n_trades = metrics["n_trades"]
        
        # Penalty for too few trades (overfitting) or too many (whipsaw)
        if n_trades < 10 or n_trades > 85:
            return 1e6
        
        # Stricter penalty for drawdown > 40% to force faster exits
        dd_penalty = max(0, max_dd - 40.0) * 10.0
        
        # Composite objective
        reward = cagr * 0.6 + sharpe * 10.0 + sortino * 5.0 - dd_penalty
        
        return -reward
        
    except Exception:
        return 1e6

# ─── Main ──────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} days from {df.index[0]} to {df.index[-1]}")
    
    # Parameter bounds:
    # [ema_span_entry, ema_span_exit, score_entry, score_exit, cb_activate, cb_cooloff, comp_entry_boost, use_bear]
    bounds = [
        (5, 30),         # ema_span_entry
        (2, 8),          # ema_span_exit (force fast exit response)
        (0.05, 0.80),    # score_entry (go to 100%)
        (-0.30, 0.50),   # score_exit (go to 0%)
        (-3.0, -0.5),    # cb_activate (composite <= this → force 0%)
        (-1.0, 1.0),     # cb_cooloff (composite > this → allow re-entry)
        (1.9, 3.2),      # comp_entry_boost (restrict to prevent mid-trend whipsaws)
        (0.0, 1.0),      # use_bear (>0.5 = True)
    ]
    
    print(f"\nRunning Differential Evolution (8 parameters)...")
    print(f"  Bounds: {bounds}\n")
    
    result = differential_evolution(
        objective,
        bounds,
        args=(df,),
        maxiter=75,
        popsize=25,
        tol=1e-6,
        seed=42,
        disp=True,
        workers=1,
        mutation=(0.5, 1.5),
        recombination=0.8,
        polish=True,
    )
    
    # Extract best params
    x = result.x
    best_params = {
        "ema_span_entry": max(2, int(round(x[0]))),
        "ema_span_exit": max(2, int(round(x[1]))),
        "score_entry": x[2],
        "score_exit": x[3],
        "use_bear_override": bool(x[7] > 0.5),
        "cb_activate": x[4],
        "cb_cooloff": x[5],
        "comp_entry_boost": x[6],
    }
    
    print(f"\n{'='*60}")
    print(f"BEST PARAMETERS:")
    print(f"{'='*60}")
    for k, v in best_params.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.6f}")
        else:
            print(f"  {k}: {v}")
    
    # Run final simulation with best params
    equity, exposures, strat_returns = simulate_binary(df, best_params, return_series=True)
    metrics = calc_metrics(equity, strat_returns, df)
    
    print(f"\n{'='*60}")
    print(f"PERFORMANCE METRICS:")
    print(f"{'='*60}")
    print(f"  Strategy Return: {metrics['total_return']:.2f}%")
    print(f"  Buy & Hold Return: {metrics['bh_return']:.2f}%")
    print(f"  Strategy CAGR: {metrics['cagr']:.2f}%")
    print(f"  Buy & Hold CAGR: {metrics['bh_cagr']:.2f}%")
    print(f"  Max Drawdown: {metrics['max_dd']:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe']:.2f}")
    print(f"  Sortino Ratio: {metrics['sortino']:.2f}")
    print(f"  Calmar Ratio: {metrics['calmar']:.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Total Trades: {metrics['n_trades']}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    
    # Save best params for later use
    import json
    output = {
        "params": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in best_params.items()},
        "metrics": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in metrics.items()},
        "raw_x": [float(xi) for xi in result.x],
        "objective_value": float(result.fun),
    }
    
    with open("tmp/optimize_binary_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to tmp/optimize_binary_results.json")

if __name__ == "__main__":
    main()
