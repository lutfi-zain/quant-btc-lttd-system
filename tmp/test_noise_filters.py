import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import sqlite3
import pandas as pd
import numpy as np

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, o.close
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
    """
    John Ehlers' 2-pole SuperSmoother filter.
    """
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

def simulate_with_filters(df, params, filter_mode="none", filter_param=0):
    ema_entry = params["ema_span_entry"]
    ema_exit = params["ema_span_exit"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    use_bear = params["use_bear_override"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    comp_entry_boost = params["comp_entry_boost"]
    
    # 1. Choose smoothing method
    if filter_mode == "supersmoother":
        smoothed_entry = super_smoother(df["final_score"], period=ema_entry)
        smoothed_exit = super_smoother(df["final_score"], period=ema_exit)
    else:
        smoothed_entry = df["final_score"].ewm(span=ema_entry, adjust=False).mean()
        smoothed_exit = df["final_score"].ewm(span=ema_exit, adjust=False).mean()
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    
    # Noise tracking variables
    days_in_position = 0
    days_since_exit = 999
    
    for i in range(len(df)):
        score_ent = smoothed_entry.iloc[i]
        score_ex = smoothed_exit.iloc[i]
        regime = df["regime"].iloc[i]
        comp = df["composite_value"].iloc[i]
        
        exp = prev_exp
        
        # Increment timers
        if prev_exp >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
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
            # Apply Minimum Holding Period (MHP)
            if filter_mode == "mhp" and days_in_position < filter_param:
                exp = 1.0  # Force hold
            else:
                if score_ex <= score_exit:
                    exp = 0.0
        else:  # currently OUT
            # Apply Re-entry Cool-off (RCO)
            if filter_mode == "rco" and days_since_exit < filter_param:
                exp = 0.0  # Force out
            else:
                if score_ent >= score_entry:
                    exp = 1.0
        
        # BEAR regime override
        if use_bear and regime == "BEAR":
            exp = 0.0
            
        # Composite value entry boost (accumulation)
        if comp >= comp_entry_boost and exp == 0.0:
            if filter_mode != "rco" or days_since_exit >= filter_param:
                exp = 1.0
        
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

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

df = load_data()
target = get_user_target_exposure(df.index)

# Original optimized params
params = {
    "ema_span_entry": 19,
    "ema_span_exit": 7,
    "score_entry": 0.543530,
    "score_exit": 0.469470,
    "cb_activate": -2.029922,
    "cb_cooloff": 0.556041,
    "comp_entry_boost": 1.964654,
    "use_bear_override": False
}

print("==========================================================================")
print("                    NOISE REDUCTION FILTER EVALUATION                     ")
print("==========================================================================")

# 1. Baseline
exp_base = simulate_with_filters(df, params, filter_mode="none")
cagr, sharpe, max_dd, trades = calculate_metrics(df, exp_base)
mis = np.sum(exp_base != target.values)
acc = (1 - mis/len(df)) * 100
print(f"BASELINE (EMA Smoothing):")
print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | Max DD: {max_dd:.2f}% | Trades: {trades} | Mismatch: {mis} ({acc:.2f}%)")

# 2. SuperSmoother
print("\n--- John Ehlers SuperSmoother (Replacing EMA) ---")
for entry_p in [10, 15, 20]:
    for exit_p in [5, 8, 12]:
        if entry_p < exit_p: continue
        p_temp = params.copy()
        p_temp["ema_span_entry"] = entry_p
        p_temp["ema_span_exit"] = exit_p
        exp_ss = simulate_with_filters(df, p_temp, filter_mode="supersmoother")
        cagr_ss, sharpe_ss, max_dd_ss, trades_ss = calculate_metrics(df, exp_ss)
        mis_ss = np.sum(exp_ss != target.values)
        acc_ss = (1 - mis_ss/len(df)) * 100
        print(f"  SuperSmoother(Entry={entry_p}, Exit={exit_p}):")
        print(f"    CAGR: {cagr_ss:.2f}% | Sharpe: {sharpe_ss:.4f} | Max DD: {max_dd_ss:.2f}% | Trades: {trades_ss} | Mismatch: {mis_ss} ({acc_ss:.2f}%)")

# 3. Minimum Holding Period (MHP)
print("\n--- Minimum Holding Period (MHP) ---")
for h_days in [3, 5, 7, 10]:
    exp_mhp = simulate_with_filters(df, params, filter_mode="mhp", filter_param=h_days)
    cagr_mhp, sharpe_mhp, max_dd_mhp, trades_mhp = calculate_metrics(df, exp_mhp)
    mis_mhp = np.sum(exp_mhp != target.values)
    acc_mhp = (1 - mis_mhp/len(df)) * 100
    print(f"  MHP = {h_days} days:")
    print(f"    CAGR: {cagr_mhp:.2f}% | Sharpe: {sharpe_mhp:.4f} | Max DD: {max_dd_mhp:.2f}% | Trades: {trades_mhp} | Mismatch: {mis_mhp} ({acc_mhp:.2f}%)")

# 4. Re-entry Cool-off (RCO)
print("\n--- Re-entry Cool-off (RCO) ---")
for c_days in [3, 5, 7, 10]:
    exp_rco = simulate_with_filters(df, params, filter_mode="rco", filter_param=c_days)
    cagr_rco, sharpe_rco, max_dd_rco, trades_rco = calculate_metrics(df, exp_rco)
    mis_rco = np.sum(exp_rco != target.values)
    acc_rco = (1 - mis_rco/len(df)) * 100
    print(f"  RCO = {c_days} days:")
    print(f"    CAGR: {cagr_rco:.2f}% | Sharpe: {sharpe_rco:.4f} | Max DD: {max_dd_rco:.2f}% | Trades: {trades_rco} | Mismatch: {mis_rco} ({acc_rco:.2f}%)")
