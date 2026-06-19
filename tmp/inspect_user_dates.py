import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, d.circuit_breaker_active, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    df.set_index("date", inplace=True)
    
    # Load composite values
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

    # Let's inspect the specific dates
    dates = [
        "2016-01-26", "2016-08-09", "2017-01-28", "2017-07-14", "2017-09-25",
        "2018-01-16", "2018-08-18", "2019-04-09", "2019-07-30", "2020-03-10",
        "2020-05-23", "2021-09-18", "2021-09-25", "2021-11-30", "2023-08-01"
    ]
    
    print("INSULATION DETAILS FOR USER DATES:")
    print("="*80)
    for d_str in dates:
        ts = pd.Timestamp(d_str)
        if ts in df.index:
            row = df.loc[ts]
            # print window around the date (e.g. 5 days before, 5 days after) to see context
            print(f"\n--- Context around {d_str} (close: ${row['close']:,.2f}) ---")
            start = ts - pd.Timedelta(days=3)
            end = ts + pd.Timedelta(days=3)
            window = df.loc[start:end]
            for w_ts, w_row in window.iterrows():
                marker = ">>>" if w_ts == ts else "   "
                print(f"{marker} {w_ts.strftime('%Y-%m-%d')}: close=${w_row['close']:8.2f} | regime={w_row['regime']:8} | score={w_row['final_score']:6.3f} | exposure={w_row['target_exposure']:.1f} | comp={w_row['composite_value']:6.3f} | cb={w_row['circuit_breaker_active']}")

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
