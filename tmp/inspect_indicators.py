import sqlite3
import pandas as pd
import numpy as np
import sys, os

def inspect_indicators_for_range(start_date, end_date):
    conn = sqlite3.connect("database/lttd.db")
    
    # 1. Fetch raw scores and indicator values
    df_scores = pd.read_sql(f"""
        SELECT date, final_score, regime, target_exposure
        FROM daily_lttd
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date
    """, conn, parse_dates=["date"])
    
    if df_scores.empty:
        print(f"No records found for range {start_date} to {end_date}")
        conn.close()
        return
        
    df_scores.set_index("date", inplace=True)
    
    # Get all indicators in database
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT indicator_name FROM indicator_scores")
    indicators = [r[0] for r in cursor.fetchall()]
    
    # Fetch all indicator values for this date range
    df_ind_pivot = pd.read_sql(f"""
        SELECT date, indicator_name, score
        FROM indicator_scores
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
    """, conn, parse_dates=["date"])
    
    conn.close()
    
    if not df_ind_pivot.empty:
        df_ind = df_ind_pivot.pivot(index="date", columns="indicator_name", values="score")
        df_merged = df_scores.join(df_ind, how="left")
    else:
        df_merged = df_scores
        
    print(f"\n==========================================================================")
    print(f"Indicators for Range: {start_date} to {end_date}")
    print(f"==========================================================================")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df_merged)

def main():
    print("Checking indicators for the three target periods:")
    inspect_indicators_for_range("2017-01-15", "2017-01-29")
    inspect_indicators_for_range("2021-02-05", "2021-02-15")
    inspect_indicators_for_range("2021-09-28", "2021-10-12")

if __name__ == "__main__":
    main()
