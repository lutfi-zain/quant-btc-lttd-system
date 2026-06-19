import sqlite3
import pandas as pd
import numpy as np

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df["simple_return"] = df["close"].pct_change().fillna(0.0)
    
    target_df = pd.read_csv("docs/isps/isp-signals-btcusd-2026-06-13.csv")
    target_df["Date"] = pd.to_datetime(target_df["Date"])
    target_df.set_index("Date", inplace=True)
    
    # Create daily position
    df["target_pct"] = 0.0
    
    last_pct = 0.0
    for t in df.index:
        if t in target_df.index:
            action = target_df.loc[t, "Action"]
            pct = target_df.loc[t, "EquityPct"]
            if action == "SELL" and pct == 100:
                last_pct = 0.0
            elif pct == 100:
                last_pct = 1.0
            elif pct == 50:
                last_pct = 0.5
        df.loc[t, "target_pct"] = last_pct
        
    df["strat_return"] = df["target_pct"].shift(1).fillna(0.0) * df["simple_return"]
    df["equity"] = (1 + df["strat_return"]).cumprod()
    
    total_ret = df["equity"].iloc[-1]
    years = (df.index.max() - df.index.min()).days / 365.25
    cagr = (total_ret ** (1/years) - 1) * 100
    
    peak = df["equity"].cummax()
    dd = (df["equity"] - peak) / peak
    max_dd = dd.min() * 100
    
    print(f"Target Perfect Eq Return: {(total_ret - 1) * 100:.2f}%")
    print(f"Target Perfect Eq CAGR: {cagr:.2f}%")
    print(f"Target Max DD: {max_dd:.2f}%")

if __name__ == "__main__":
    main()
