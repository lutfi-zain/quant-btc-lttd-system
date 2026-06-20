import sqlite3

def main():
    conn = sqlite3.connect("database/lttd.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(indicator_scores);")
    print("indicator_scores columns:")
    for col in cursor.fetchall():
        print(col)
    conn.close()

if __name__ == '__main__':
    main()
