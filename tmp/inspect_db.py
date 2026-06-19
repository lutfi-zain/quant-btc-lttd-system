import sqlite3

def main():
    conn = sqlite3.connect("database/lttd.db")
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Get schema of daily_lttd
    cursor.execute("PRAGMA table_info(daily_lttd);")
    print("\ndaily_lttd columns:")
    for col in cursor.fetchall():
        print(col)
        
    # Get schema of ohlcv
    cursor.execute("PRAGMA table_info(ohlcv);")
    print("\nohlcv columns:")
    for col in cursor.fetchall():
        print(col)
        
    conn.close()

if __name__ == '__main__':
    main()
