import sqlite3
import pandas as pd
import numpy as np
import sys, os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.data.valuation_api_client import ValuationApiClient
from src.execution.sizing import super_smoother, SUPERSMOOTHER_PERIOD_ENTRY, SUPERSMOOTHER_PERIOD_EXIT

def investigate_range(start_date, end_date):
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql(f"""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, d.circuit_breaker_active, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        WHERE d.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    
    if df.empty:
        print(f"No records found for range {start_date} to {end_date}")
        return
        
    df.set_index("date", inplace=True)
    
    # Load composite valuation values
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
    
    # Let's load ALL scores to compute Ehlers SuperSmoother
    conn = sqlite3.connect("database/lttd.db")
    all_df = pd.read_sql("""
        SELECT d.date, d.final_score
        FROM daily_lttd d
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    all_df.set_index("date", inplace=True)
    
    smoothed_entry = super_smoother(all_df["final_score"], period=SUPERSMOOTHER_PERIOD_ENTRY)
    smoothed_exit = super_smoother(all_df["final_score"], period=SUPERSMOOTHER_PERIOD_EXIT)
    
    df["smoothed_entry"] = smoothed_entry.loc[df.index]
    df["smoothed_exit"] = smoothed_exit.loc[df.index]
    
    # Add rolling MA-229
    conn = sqlite3.connect("database/lttd.db")
    all_ohlcv = pd.read_sql("SELECT DATE(timestamp) as date, close FROM ohlcv ORDER BY timestamp", conn, parse_dates=["date"])
    conn.close()
    all_ohlcv.set_index("date", inplace=True)
    ma_229 = all_ohlcv["close"].rolling(229).mean()
    df["ma_229"] = ma_229.loc[df.index]
    
    print(f"\n==========================================================================")
    print(f"Investigation Range: {start_date} to {end_date}")
    print(f"==========================================================================")
    
    print(f"{'Date':11} | {'Close':9} | {'MA-229':9} | {'Regime':8} | {'Final':6} | {'Sm Entry':8} | {'Sm Exit':8} | {'Comp':7} | {'Exposure':8} | {'CB':2}")
    print("-" * 115)
    for idx, row in df.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        print(f"{date_str:11} | {row['close']:9.2f} | {row['ma_229']:9.2f} | {row['regime']:8} | {row['final_score']:6.4f} | {row['smoothed_entry']:8.4f} | {row['smoothed_exit']:8.4f} | {row['composite_value']:7.4f} | {row['target_exposure']:8.1f} | {int(row['circuit_breaker_active']):2}")

def main():
    # 1. Jan 2017 Range
    investigate_range("2017-01-05", "2017-02-05")
    
    # 2. Feb 2021 Range
    investigate_range("2021-02-01", "2021-02-25")
    
    # 3. Oct 2021 Range
    investigate_range("2021-09-25", "2021-10-15")

if __name__ == "__main__":
    main()
