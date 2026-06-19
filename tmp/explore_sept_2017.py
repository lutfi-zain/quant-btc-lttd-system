import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT date, regime, final_score, target_exposure
        FROM daily_lttd
        WHERE date BETWEEN '2017-09-15' AND '2017-09-28'
        ORDER BY date
    """, conn, parse_dates=["date"])
    conn.close()
    
    from src.execution.sizing import EMA_SPAN_ENTRY, EMA_SPAN_EXIT
    # Let's recalculate smoothed scores
    # To get correct EMAs we need some history, so let's load all data up to 2017-09-28
    conn = sqlite3.connect("database/lttd.db")
    all_df = pd.read_sql("""
        SELECT date, final_score
        FROM daily_lttd
        WHERE date <= '2017-09-28'
        ORDER BY date
    """, conn, parse_dates=["date"])
    conn.close()
    
    all_df["smoothed_entry"] = all_df["final_score"].ewm(span=EMA_SPAN_ENTRY, adjust=False).mean()
    all_df["smoothed_exit"] = all_df["final_score"].ewm(span=EMA_SPAN_EXIT, adjust=False).mean()
    
    merged = df.merge(all_df[["date", "smoothed_entry", "smoothed_exit"]], on="date")
    for _, row in merged.iterrows():
        print(f"{row['date'].strftime('%Y-%m-%d')}: score={row['final_score']:6.4f} | smooth_entry={row['smoothed_entry']:6.4f} | smooth_exit={row['smoothed_exit']:6.4f} | exposure={row['target_exposure']:.1f}")

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
