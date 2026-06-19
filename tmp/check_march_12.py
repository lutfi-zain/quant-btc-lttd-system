import sqlite3
import requests
import datetime
import pandas as pd

def main():
    # 1. Check SQLite
    conn = sqlite3.connect("database/lttd.db")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, close FROM ohlcv WHERE timestamp LIKE '2020-03%' ORDER BY timestamp")
    rows_sqlite = cursor.fetchall()
    conn.close()
    
    print("--- SQLite 2020-03 ---")
    for r in rows_sqlite[:15]:
        print(r)
        
    # 2. Check API
    # Let's fetch starting from 2020-03-01
    url = "https://bitview.space/api/series/price_ohlc/day?start=2020-03-01"
    resp = requests.get(url).json()
    start_idx = resp["start"]
    data = resp["data"]
    
    # We will try both base dates: 2009-01-01 and 2009-01-03
    base_1 = datetime.date(2009, 1, 1)
    base_3 = datetime.date(2009, 1, 3)
    
    print("\n--- API data with Base Date 2009-01-01 ---")
    for i, row in enumerate(data[:15]):
        dt = base_1 + datetime.timedelta(days=start_idx + i)
        print(f"{dt}: {row[3]}") # close is index 3
        
    print("\n--- API data with Base Date 2009-01-03 ---")
    for i, row in enumerate(data[:15]):
        dt = base_3 + datetime.timedelta(days=start_idx + i)
        print(f"{dt}: {row[3]}")

if __name__ == '__main__':
    main()
