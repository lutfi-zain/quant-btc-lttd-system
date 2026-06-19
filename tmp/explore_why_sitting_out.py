import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    conn = sqlite3.connect("database/lttd.db")
    # check columns in daily_lttd
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(daily_lttd)")
    cols = [c[1] for c in cursor.fetchall()]
    print("Columns in daily_lttd:", cols)
    
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, d.circuit_breaker_active, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        WHERE d.date BETWEEN '2017-05-01' AND '2017-12-31'
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    
    # We want to see how many days each factor was active
    print(f"Total days: {len(df)}")
    print("Regime counts:")
    print(df["regime"].value_counts())
    
    cb_active_days = df["circuit_breaker_active"].sum() if "circuit_breaker_active" in df.columns else 0
    print(f"Circuit breaker active days: {cb_active_days}")
    
    # Recalculate SuperSmoother scores
    from src.execution.sizing import SUPERSMOOTHER_PERIOD_ENTRY, SUPERSMOOTHER_PERIOD_EXIT, super_smoother
    conn = sqlite3.connect("database/lttd.db")
    all_df = pd.read_sql("""
        SELECT date, final_score
        FROM daily_lttd
        WHERE date <= '2017-12-31'
        ORDER BY date
    """, conn, parse_dates=["date"])
    conn.close()
    
    all_df["smoothed_entry"] = super_smoother(all_df["final_score"], period=SUPERSMOOTHER_PERIOD_ENTRY)
    all_df["smoothed_exit"] = super_smoother(all_df["final_score"], period=SUPERSMOOTHER_PERIOD_EXIT)
    
    merged = df.merge(all_df[["date", "smoothed_entry", "smoothed_exit"]], on="date")
    
    print("\nSample records where target_exposure is 0.0 but price is rising (e.g. July-Sept 2017):")
    # print every 10 days
    for idx, row in merged.iterrows():
        if idx % 10 == 0:
            print(f"{row['date'].strftime('%Y-%m-%d')}: close=${row['close']:,.2f} | score={row['final_score']:6.4f} | smooth_ent={row['smoothed_entry']:6.4f} | smooth_ex={row['smoothed_exit']:6.4f} | regime={row['regime']} | cb={row['circuit_breaker_active']} | exposure={row['target_exposure']:.1f}")

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
