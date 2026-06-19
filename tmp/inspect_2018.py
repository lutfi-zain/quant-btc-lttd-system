import sqlite3
import pandas as pd
import numpy as np

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, d.circuit_breaker_active, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        WHERE d.date BETWEEN '2018-01-01' AND '2018-12-31'
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()

    df['position'] = df['target_exposure']
    df['prev_position'] = df['position'].shift(1).fillna(0.0)
    df['trade_trigger'] = df['position'] != df['prev_position']

    trade_days = df[df['position'] > 0.0]
    print(f"Total days in position during 2018: {len(trade_days)}")

    print("\nAll exposure transitions in 2018:")
    for idx, row in df.iterrows():
        if row['trade_trigger']:
            print(f"  {row['date'].strftime('%Y-%m-%d')}: position changed from {row['prev_position']} to {row['position']} | close=${row['close']:,.2f} | score={row['final_score']:6.3f} | regime={row['regime']} | cb={row['circuit_breaker_active']}")

    print("\nDetails of the trade periods in 2018:")
    # print the start and end of each period where exposure was > 0
    in_pos = False
    start_row = None
    for idx, row in df.iterrows():
        if row['position'] > 0.0 and not in_pos:
            in_pos = True
            start_row = row
        elif row['position'] == 0.0 and in_pos:
            in_pos = False
            # print details
            print(f"Trade: {start_row['date'].strftime('%Y-%m-%d')} to {row['date'].strftime('%Y-%m-%d')} | Start Price: ${start_row['close']:,.2f} | End Price: ${row['close']:,.2f} | Return: {((row['close'] / start_row['close']) - 1) * 100:.2f}%")
    if in_pos:
        print(f"Trade: {start_row['date'].strftime('%Y-%m-%d')} to end of 2018 | Start Price: ${start_row['close']:,.2f} | End Price: ${df.iloc[-1]['close']:,.2f} | Return: {((df.iloc[-1]['close'] / start_row['close']) - 1) * 100:.2f}%")

if __name__ == '__main__':
    main()
