import sqlite3
import pandas as pd
import numpy as np
import sys, os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.data.valuation_api_client import ValuationApiClient
from src.execution.sizing import super_smoother

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

def simulate_dynamic_exit(df, params):
    entry_p = params["entry_p"]
    exit_p = params["exit_p"]
    score_entry = params["score_entry"]
    score_exit_bull = params["score_exit_bull"]
    score_exit_bear = params["score_exit_bear"]
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
        price = df["close"].iloc[i]
        ma_val = df["ma_val"].iloc[i]
        
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
                # Dynamic exit threshold based on MA
                ma_condition = (price > ma_val) if not pd.isna(ma_val) else True
                current_exit_threshold = score_exit_bull if ma_condition else score_exit_bear
                
                if score_ex <= current_exit_threshold:
                    exp = 0.0
        else:  # OUT position
            if days_since_exit >= rco_days:
                ma_condition = (price > ma_val) if not pd.isna(ma_val) else True
                if score_ent >= score_entry and ma_condition:
                    exp = 1.0
            
        # Deep value boost override
        if comp >= 2.000613 and exp == 0.0:
            if days_since_exit >= rco_days:
                exp = 1.0
            
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

def calculate_metrics(df, exposures):
    close = df["close"].values
    simple_ret = (close[1:] - close[:-1]) / close[:-1]
    strat_ret = simple_ret * exposures[:-1]
    
    equity = np.cumprod(1 + strat_ret)
    years = len(strat_ret) / 365.25
    cagr = (equity[-1] ** (1 / years) - 1) * 100 if len(equity) > 0 and equity[-1] > 0 else 0.0
    
    std = np.std(strat_ret) * np.sqrt(365)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365) if std > 0 else 0
    
    peaks = np.maximum.accumulate(equity)
    dd = (equity - peaks) / peaks
    max_dd = np.min(dd) * 100
    
    trades = np.sum(np.diff(exposures) != 0)
    
    return cagr, sharpe, max_dd, trades

def check_dates(df, exposures):
    dates_to_check = [
        ("2017-01-18", "2017-01-29"),
        ("2021-02-05", "2021-02-15"),
        ("2021-09-28", "2021-10-12")
    ]
    for start, end in dates_to_check:
        print(f"\nExposure for range {start} to {end}:")
        sub = df.loc[start:end].copy()
        sub["pos"] = exposures[df.index.get_loc(start):df.index.get_loc(end)+1]
        for idx, row in sub.iterrows():
            print(f"  {idx.strftime('%Y-%m-%d')}: close={row['close']:9.2f} | exposure={row['pos']}")

def main():
    df = load_data()
    
    # Pre-calculate MA on the full dataset
    df["ma_val"] = df["close"].rolling(229).mean()
    
    # Align with 52-day warmup
    df = df.iloc[52:]
    
    # Original Optimized params
    params = {
        "entry_p": 8,
        "exit_p": 5,
        "score_entry": 0.359164,
        "score_exit_bull": 0.324482,
        "score_exit_bear": 0.324482,
        "cb_activate": -2.829015,
        "cb_cooloff": 0.712335,
        "rco_days": 4,
        "mhp_days": 12,
        "ma_period": 229
    }
    
    print("Baseline (Fixed Exit at 0.3245):")
    exp_base = simulate_dynamic_exit(df, params)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp_base)
    print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | MaxDD: {max_dd:.2f}% | Trades: {trades}")
    check_dates(df, exp_base)
    
    print("\n" + "="*50)
    print("Testing dynamic exit: lower exit threshold in bull market (e.g. score_exit_bull = 0.05)")
    params["score_exit_bull"] = 0.05
    exp_dyn = simulate_dynamic_exit(df, params)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp_dyn)
    print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | MaxDD: {max_dd:.2f}% | Trades: {trades}")
    check_dates(df, exp_dyn)
    
    print("\n" + "="*50)
    print("Testing dynamic exit: even lower exit threshold in bull market (e.g. score_exit_bull = -0.10)")
    params["score_exit_bull"] = -0.10
    exp_dyn2 = simulate_dynamic_exit(df, params)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp_dyn2)
    print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | MaxDD: {max_dd:.2f}% | Trades: {trades}")
    check_dates(df, exp_dyn2)

if __name__ == "__main__":
    main()
