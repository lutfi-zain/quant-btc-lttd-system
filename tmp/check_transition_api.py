import requests
import datetime
import pandas as pd
import sqlite3

def main():
    # Fetch from API
    url = "https://bitview.space/api/series/price_ohlc/day?start=2017-07-25"
    resp = requests.get(url).json()
    start_idx = resp["start"]
    data = resp["data"]
    
    base_date = datetime.date(2009, 1, 1)
    
    print("--- API close prices ---")
    api_prices = {}
    for i, row in enumerate(data):
        dt = base_date + datetime.timedelta(days=start_idx + i)
        if dt >= datetime.date(2017, 7, 25) and dt <= datetime.date(2017, 8, 5):
            print(f"{dt}: {row[3]}")
            api_prices[dt] = row[3]
            
    # SQLite
    conn = sqlite3.connect("database/lttd.db")
    df_sql = pd.read_sql(
        "SELECT timestamp, close FROM ohlcv WHERE timestamp >= '2017-07-25 00:00:00' AND timestamp <= '2017-08-05 00:00:00' ORDER BY timestamp",
        conn
    )
    conn.close()
    
    print("\n--- SQLite close prices ---")
    for _, row in df_sql.iterrows():
        dt_str = row['timestamp'][:10]
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d").date()
        api_val = api_prices.get(dt, None)
        diff = row['close'] - api_val if api_val is not None else None
        print(f"{dt}: SQL={row['close']:.2f} | API={api_val} | Diff={diff}")

if __name__ == '__main__':
    main()
