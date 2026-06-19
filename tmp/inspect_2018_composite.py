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
        WHERE d.date BETWEEN '2018-01-01' AND '2018-12-31'
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    
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
    
    df.set_index("date", inplace=True)
    
    print("Trade dates and their composite values in 2018:")
    trade_dates = ['2018-05-08', '2018-08-01', '2018-09-11']
    for d in trade_dates:
        row = df.loc[d]
        print(f"Date: {d} | close: ${row['close']:,.2f} | score: {row['final_score']:.3f} | composite_value: {row['composite_value']:.4f}")

    print("\nSummary of composite_value in 2018:")
    print(df["composite_value"].describe())

if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
