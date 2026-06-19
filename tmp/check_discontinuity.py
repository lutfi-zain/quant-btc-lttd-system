import sqlite3
import pandas as pd

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql(
        "SELECT timestamp, open, high, low, close FROM ohlcv WHERE timestamp >= '2017-07-20 00:00:00' AND timestamp <= '2017-08-10 00:00:00' ORDER BY timestamp",
        conn
    )
    conn.close()
    
    print("--- SQLite Price Data around Aug 1, 2017 ---")
    print(df.to_string())

if __name__ == '__main__':
    main()
