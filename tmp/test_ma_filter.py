import sqlite3
import pandas as pd
import numpy as np
import os, sys

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

def simulate_with_ma_filter(df, params, use_ma_filter=False, ma_period=200):
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
    
    # 200-day MA
    ma = df["close"].rolling(ma_period).mean()
    
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
        ma_val = ma.iloc[i]
        
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
                # Add MA filter to entry check
                ma_condition = True
                if use_ma_filter and not pd.isna(ma_val):
                    ma_condition = (price > ma_val)
                    
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

def main():
    df = load_data()
    df = df.iloc[52:]
    
    params = {
        "entry_p": 8,
        "exit_p": 4,
        "score_entry": 0.435160,
        "score_exit": 0.294856,
        "cb_activate": -3.386067,
        "cb_cooloff": 0.789564,
        "rco_days": 3,
        "mhp_days": 12
    }
    
    print("Baseline (No MA filter):")
    cagr, sharpe, max_dd, trades = calculate_metrics(df, simulate_with_ma_filter(df, params, use_ma_filter=False))
    print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | MaxDD: {max_dd:.2f}% | Trades: {trades}")
    
    # Check 2018 trades specifically in Baseline
    exp_base = simulate_with_ma_filter(df, params, use_ma_filter=False)
    # print 2018 trades
    print("\nTrades in 2018 (Baseline):")
    df_2018 = df.loc['2018-01-01':'2018-12-31'].copy()
    df_2018['pos'] = exp_base[df.index.get_loc('2018-01-01'):df.index.get_loc('2018-12-31')+1]
    df_2018['prev_pos'] = df_2018['pos'].shift(1).fillna(0.0)
    for idx, row in df_2018.iterrows():
        if row['pos'] != row['prev_pos']:
            print(f"  {idx.strftime('%Y-%m-%d')}: changed to {row['pos']} | close=${row['close']:,.2f}")
            
    print("\n" + "="*50)
    print("Testing different MA filter periods:")
    for period in [50, 100, 150, 200, 250, 300]:
        cagr, sharpe, max_dd, trades = calculate_metrics(df, simulate_with_ma_filter(df, params, use_ma_filter=True, ma_period=period))
        print(f"  MA-{period} filter: CAGR: {cagr:.2f}% | Sharpe: {sharpe:.4f} | MaxDD: {max_dd:.2f}% | Trades: {trades}")
        
        # Check 2018 trades
        exp_ma = simulate_with_ma_filter(df, params, use_ma_filter=True, ma_period=period)
        df_2018['pos'] = exp_ma[df.index.get_loc('2018-01-01'):df.index.get_loc('2018-12-31')+1]
        df_2018['prev_pos'] = df_2018['pos'].shift(1).fillna(0.0)
        trades_2018 = []
        for idx, row in df_2018.iterrows():
            if row['pos'] != row['prev_pos']:
                trades_2018.append(f"{idx.strftime('%Y-%m-%d')} ({row['pos']})")
        print(f"    2018 transitions: {', '.join(trades_2018)}")

if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
