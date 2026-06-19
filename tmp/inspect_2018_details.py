import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    
    from src.execution.sizing import SUPERSMOOTHER_PERIOD_ENTRY, SUPERSMOOTHER_PERIOD_EXIT, super_smoother
    df["smoothed_entry"] = super_smoother(df["final_score"], period=SUPERSMOOTHER_PERIOD_ENTRY)
    df["smoothed_exit"] = super_smoother(df["final_score"], period=SUPERSMOOTHER_PERIOD_EXIT)
    
    df.set_index("date", inplace=True)
    
    # Inspect around 2018-05-08
    print("--- Around 2018-05-08 ---")
    print(df.loc['2018-05-01':'2018-05-12', ['regime', 'final_score', 'smoothed_entry', 'target_exposure', 'close']])
    
    # Inspect around 2018-08-01
    print("\n--- Around 2018-08-01 ---")
    print(df.loc['2018-07-25':'2018-08-05', ['regime', 'final_score', 'smoothed_entry', 'target_exposure', 'close']])
    
    # Inspect around 2018-09-11
    print("\n--- Around 2018-09-11 ---")
    print(df.loc['2018-09-05':'2018-09-15', ['regime', 'final_score', 'smoothed_entry', 'target_exposure', 'close']])

if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
