import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import sqlite3
import pandas as pd
import numpy as np

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

def get_user_target_exposure(dates):
    target = pd.Series(0.0, index=dates)
    
    # Jan 1 to Jan 25, 2017: No trade (0.0)
    target.loc["2017-01-01":"2017-01-25"] = 0.0
    
    # Rule 1 & 2: Bull market 2017 (after July correction)
    # Entry July 29, 2017 to exit Jan 10, 2018
    target.loc["2017-07-29":"2018-01-10"] = 1.0
    
    # Rule 5: Jan 10, 2020 to Mar 4, 2020
    target.loc["2020-01-10":"2020-03-04"] = 1.0
    
    # Rule 6: Mar 16, 2020 to Apr 27, 2021
    target.loc["2020-03-16":"2021-04-27"] = 1.0
    
    # Rule 8: July 23, 2021 to Nov 28, 2021
    target.loc["2021-07-23":"2021-11-28"] = 1.0
    
    # Rule 11 & 12: Oct 22, 2023 to Apr 15, 2024
    target.loc["2023-10-22":"2024-04-15"] = 1.0
    
    # Rule 14: Oct 1, 2024 to Feb 15, 2025
    target.loc["2024-10-01":"2025-02-15"] = 1.0
    
    # Rule 17: Apr 20, 2025 to Oct 23, 2025
    target.loc["2025-04-20":"2025-10-23"] = 1.0
    
    # For periods not explicitly mentioned by the user as trade or no-trade,
    # let's assume they are "neutral" and we don't penalize them in our target.
    # Wait, the user did say:
    # 20 Dec 2018 to 1 Mar 2019: No trade (0.0)
    target.loc["2018-12-20":"2019-03-01"] = 0.0
    
    # Noise dates: Sept 22, 2017 (no cut loss, should be 1.0)
    target.loc["2017-09-22"] = 1.0
    # Jan 9 and 11, 2018: Exit early, so should be 0.0 or 1.0?
    # User: "tidak suka contohnya seperti di 22 September 2017, 9 Januari dan 11 Januari 2018... lagging"
    # Jan 9-11 2018 was right at the top of the bull run. The user wants a quick exit here. So should be 0.0.
    target.loc["2018-01-09":"2018-01-11"] = 0.0
    
    return target

# List of critical periods to check accuracy
critical_periods = [
    ("2017-01-01", "2017-01-25", "No-trade early Jan 2017"),
    ("2017-07-29", "2018-01-08", "Trade late 2017"),
    ("2018-01-09", "2018-01-11", "Exit Jan 2018 top"),
    ("2018-12-20", "2019-03-01", "No-trade bottom 2018-2019"),
    ("2020-01-10", "2020-03-04", "Trade early 2020"),
    ("2020-03-16", "2021-04-27", "Trade bull 2020-2021"),
    ("2021-07-23", "2021-11-28", "Trade late 2021"),
    ("2023-10-22", "2024-04-15", "Trade bull 2023-2024"),
    ("2024-10-01", "2025-02-15", "Trade late 2024"),
    ("2025-04-20", "2025-10-23", "Trade mid 2025")
]

def compute_ichimoku(df):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    sa = ((tenkan + kijun) / 2).shift(26)
    sb = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou = close.shift(26)
    
    df["T"] = tenkan
    df["K"] = kijun
    df["SA"] = sa
    df["SB"] = sb
    df["C"] = chikou
    return df

def simulate_binary_with_ichimoku(df, params, ichimoku_rule=None):
    ema_entry = params["ema_span_entry"]
    ema_exit = params["ema_span_exit"]
    score_entry = params["score_entry"]
    score_exit = params["score_exit"]
    use_bear = params["use_bear_override"]
    cb_activate = params["cb_activate"]
    cb_cooloff = params["cb_cooloff"]
    comp_entry_boost = params["comp_entry_boost"]
    
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
        
        # Check Ichimoku filter first if provided
        ichi_pass = True
        if ichimoku_rule == "P > SB AND P > C":
            ichi_pass = (df["close"].iloc[i] > df["SB"].iloc[i]) and (df["close"].iloc[i] > df["C"].iloc[i])
        elif ichimoku_rule == "P > SB":
            ichi_pass = df["close"].iloc[i] > df["SB"].iloc[i]
        elif ichimoku_rule == "P > C":
            ichi_pass = df["close"].iloc[i] > df["C"].iloc[i]
            
        exp = prev_exp
        
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
            if score_ex <= score_exit:
                exp = 0.0
            elif not ichi_pass:
                exp = 0.0
        else:  # currently OUT
            if score_ent >= score_entry and ichi_pass:
                exp = 1.0
        
        # BEAR regime override
        if use_bear and regime == "BEAR":
            exp = 0.0
            
        # Composite value entry boost (accumulation)
        if comp >= comp_entry_boost and exp == 0.0 and ichi_pass:
            exp = 1.0
        
        exposures[i] = exp
        prev_exp = exp
        
    return exposures

df = load_data()
df = compute_ichimoku(df)
df = df.iloc[52:]

target = get_user_target_exposure(df.index)

# Evaluate each filter
for rule in [None, "P > SB", "P > C", "P > SB AND P > C"]:
    print(f"\n======================================")
    print(f"Filter: {rule}")
    print(f"======================================")
    
    # Test original sizing params
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
    
    exp = simulate_binary_with_ichimoku(df, params, ichimoku_rule=rule)
    df_temp = df.copy()
    df_temp["exposure"] = exp
    df_temp["target"] = target
    
    # Calculate general metrics
    close = df_temp["close"].values
    log_ret = np.log(close[1:] / close[:-1])
    strat_ret = log_ret * exp[:-1]
    cagr = (np.exp(np.sum(strat_ret)) ** (365.25 / len(strat_ret)) - 1) * 100
    std = np.std(strat_ret) * np.sqrt(365.25)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365.25) if std > 0 else 0
    
    print(f"CAGR: {cagr:.2f}% | Sharpe: {sharpe:.2f} | Trades: {np.sum(np.diff(exp) != 0)}")
    
    # Mismatch counts in critical periods
    total_mis = 0
    total_days = 0
    for start, end, desc in critical_periods:
        sub = df_temp.loc[start:end]
        if len(sub) > 0:
            mis = (sub["exposure"] != sub["target"]).sum()
            total_mis += mis
            total_days += len(sub)
            print(f"  {start} to {end} ({desc}): {mis}/{len(sub)} mismatched (Avg Exp: {sub['exposure'].mean():.2f})")
    print(f"Critical Periods Accuracy: {(1 - total_mis/total_days)*100:.2f}% ({total_mis}/{total_days} mismatch)")
