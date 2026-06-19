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

def compute_ichimoku(df):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # Tenkan: 9-period midpoint
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    # Kijun: 26-period midpoint
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    
    # Senkou Span A: (Tenkan + Kijun) / 2 shifted forward 26 periods
    # Causally, the value today is the one calculated 26 days ago
    sa = ((tenkan + kijun) / 2).shift(26)
    
    # Senkou Span B: 52-period midpoint shifted forward 26 periods
    sb = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    
    # Chikou Causal: close 26 periods ago
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
            # Optional: exit if Ichimoku filter fails
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

def calculate_metrics(df, exposures):
    close = df["close"].values
    log_ret = np.log(close[1:] / close[:-1])
    # Shift exposures by 1 day to prevent lookahead
    strat_ret = log_ret * exposures[:-1]
    
    cagr = (np.exp(np.sum(strat_ret)) ** (365.25 / len(strat_ret)) - 1) * 100
    std = np.std(strat_ret) * np.sqrt(365.25)
    sharpe = (np.mean(strat_ret) / np.std(strat_ret)) * np.sqrt(365.25) if std > 0 else 0
    
    # Max DD
    cum_ret = np.exp(np.cumsum(strat_ret))
    peaks = np.maximum.accumulate(cum_ret)
    dd = (cum_ret - peaks) / peaks
    max_dd = np.min(dd) * 100
    
    trades = np.sum(np.diff(exposures) != 0)
    
    return cagr, sharpe, max_dd, trades

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

df = load_data()
df = compute_ichimoku(df)

# Drop first 52 days for Ichimoku warmup
df = df.iloc[52:]

print("--- BACKTEST COMPARING FILTERS ---")
for rule in [None, "P > SB", "P > C", "P > SB AND P > C"]:
    exp = simulate_binary_with_ichimoku(df, params, ichimoku_rule=rule)
    cagr, sharpe, max_dd, trades = calculate_metrics(df, exp)
    print(f"Filter: {rule}")
    print(f"  CAGR: {cagr:.2f}% | Sharpe: {sharpe:.2f} | Max DD: {max_dd:.2f}% | Trades: {trades}")
