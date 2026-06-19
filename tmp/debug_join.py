import sqlite3
import pandas as pd
import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date
        FROM daily_lttd d
        WHERE d.date BETWEEN '2018-01-01' AND '2018-01-05'
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    df.set_index("date", inplace=True)
    
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    
    print("df index type:", type(df.index), "tz:", df.index.tz)
    print("df index head:", df.index[:5])
    
    print("val_df date type:", type(val_df['date']), "tz:", val_df['date'].dt.tz)
    print("val_df date head:", val_df['date'].head())
    
    # Let's process val_df as in inspect_2018_composite.py
    val_df_processed = val_df.copy()
    val_df_processed["date"] = pd.to_datetime(val_df_processed["date"])
    if val_df_processed["date"].dt.tz is not None:
        # Convert or remove tz
        val_df_processed["date"] = val_df_processed["date"].dt.tz_convert(None)
    val_df_processed.set_index("date", inplace=True)
    
    print("val_df_processed index type:", type(val_df_processed.index), "tz:", val_df_processed.index.tz)
    print("val_df_processed index head:", val_df_processed.index[:5])
    
    joined = df.join(val_df_processed[["composite_value"]], how="left")
    print("joined head:")
    print(joined)

if __name__ == '__main__':
    main()
