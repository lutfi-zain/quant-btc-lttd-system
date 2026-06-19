import sqlite3
import requests
import datetime
import pandas as pd

def main():
    # 1. Read SQLite
    conn = sqlite3.connect("database/lttd.db")
    df_sqlite = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
    conn.close()
    df_sqlite['timestamp'] = pd.to_datetime(df_sqlite['timestamp'])
    
    # 2. Read Bitview API
    url = "https://bitview.space/api/series/price_ohlc/day?start=2016-01-01"
    response = requests.get(url, timeout=30)
    resp = response.json()
    start_idx = resp["start"]
    data = resp["data"]
    base_date = datetime.date(2009, 1, 1)
    dates = [base_date + datetime.timedelta(days=start_idx + i) for i in range(len(data))]
    df_api = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"], index=dates)
    df_api.index.name = 'timestamp'
    df_api = df_api.reset_index()
    df_api['timestamp'] = pd.to_datetime(df_api['timestamp'])
    
    # Compare
    print(f"SQLite rows: {len(df_sqlite)} | API rows: {len(df_api)}")
    print(f"SQLite range: {df_sqlite['timestamp'].min().date()} to {df_sqlite['timestamp'].max().date()}")
    print(f"API range: {df_api['timestamp'].min().date()} to {df_api['timestamp'].max().date()}")
    
    # Merge and compare close prices
    df_sqlite_close = df_sqlite.rename(columns={'close': 'close_sqlite'})
    df_api_close = df_api[['timestamp', 'Close']].rename(columns={'Close': 'close_api'})
    df_merge = pd.merge(df_sqlite_close, df_api_close, on='timestamp', how='inner')
    print(f"Merged rows: {len(df_merge)}")
    
    diff = (df_merge['close_sqlite'] - df_merge['close_api']).abs().max()
    print(f"Max absolute difference in close price: {diff}")
    
    # Check if there are any differences
    not_equal = df_merge[df_merge['close_sqlite'] != df_merge['close_api']]
    print(f"Number of rows with different close prices: {len(not_equal)}")
    if len(not_equal) > 0:
        print("First 5 mismatches:")
        print(not_equal.head())

if __name__ == '__main__':
    main()
