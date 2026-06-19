import sqlite3
import pandas as pd
import numpy as np

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, d.target_exposure, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    df.set_index("date", inplace=True)
    return df

def get_user_target_exposure(dates):
    target = pd.Series(0.0, index=dates)
    
    # Rule 1 & 2: Bull market 2017
    # Entry July 29, 2017 to exit Jan 10, 2018
    target.loc["2017-07-29":"2018-01-10"] = 1.0
    
    # Rule 5: Jan 10, 2020 to Mar 4, 2020
    target.loc["2020-01-10":"2020-03-04"] = 1.0
    
    # Rule 6: Mar 16, 2020 to Apr 27, 2021 (no cut loss in Sept)
    target.loc["2020-03-16":"2021-04-27"] = 1.0
    
    # Rule 8: July 23, 2021 to Nov 28, 2021
    target.loc["2021-07-23":"2021-11-28"] = 1.0
    
    # Rule 11 & 12: Oct 22, 2023 to Apr 15, 2024
    target.loc["2023-10-22":"2024-04-15"] = 1.0
    
    # Rule 14: Oct 1, 2024 to Feb 15, 2025
    target.loc["2024-10-01":"2025-02-15"] = 1.0
    
    # Rule 17: Apr 20, 2025 to Oct 23, 2025
    target.loc["2025-04-20":"2025-10-23"] = 1.0
    
    return target

df = load_data()
target = get_user_target_exposure(df.index)

# Find mismatches
df["target"] = target
df["mismatch"] = df["target_exposure"] != df["target"]

print(f"Total mismatch days: {df['mismatch'].sum()} out of {len(df)}")
print(f"Accuracy: {(1 - df['mismatch'].sum()/len(df))*100:.2f}%")

print("\n--- Detailed mismatches by rule periods ---")
periods = [
    ("2017-01-01", "2017-07-28", "No-trade early 2017"),
    ("2017-07-29", "2018-01-10", "Trade late 2017"),
    ("2018-01-11", "2020-01-09", "Bear / Sideways 2018-2019"),
    ("2020-01-10", "2020-03-04", "Trade early 2020"),
    ("2020-03-16", "2021-04-27", "Trade bull 2020-2021"),
    ("2021-04-28", "2021-07-22", "No-trade mid 2021"),
    ("2021-07-23", "2021-11-28", "Trade late 2021"),
    ("2021-11-29", "2023-10-21", "Bear / Sideways 2022-2023"),
    ("2023-10-22", "2024-04-15", "Trade bull 2023-2024"),
    ("2024-04-16", "2024-09-30", "No-trade mid 2024"),
    ("2024-10-01", "2025-02-15", "Trade late 2024"),
    ("2025-02-16", "2025-04-19", "No-trade early 2025"),
    ("2025-04-20", "2025-10-23", "Trade mid 2025")
]

for start, end, desc in periods:
    sub = df.loc[start:end]
    if len(sub) > 0:
        mis = sub["mismatch"].sum()
        pct = (1 - mis/len(sub))*100
        print(f"{start} to {end} ({desc}): {mis}/{len(sub)} mismatched ({pct:.1f}% aligned). Avg exposure: {sub['target_exposure'].mean():.2f}")
