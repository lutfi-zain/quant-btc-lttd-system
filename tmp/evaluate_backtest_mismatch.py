import pandas as pd
import numpy as np

def load_data():
    df = pd.read_csv("tmp_backtest_results.csv", parse_dates=["date"])
    df.set_index("date", inplace=True)
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)
    return df

def get_user_target_exposure(dates):
    target = pd.Series(0.0, index=dates)
    
    # Jan 1 to Jan 25, 2017: No trade (0.0)
    target.loc["2017-01-01":"2017-01-25"] = 0.0
    
    # Rule 1 & 2: Bull market 2017 (after July correction)
    # Entry July 29, 2017 to exit Jan 10, 2018
    target.loc["2017-07-29":"2018-01-10"] = 1.0
    
    # Rule 5: Jan 10, 2020 to Mar 4, 2020
    target.loc["2020-01-10":"2020-03-04"] = 1.0
    
    # Rule 6: Mar 16, 2020 to Apr 27, 2021
    target.loc["2020-03-16":"2021-04-27"] = 1.0
    
    # Rule 8: July 23, 2021 to Nov 28, 2021
    target.loc["2021-07-23":"2021-11-28"] = 1.0
    
    # Rule 11 & 12: Oct 22, 2023 to Apr 15, 2024
    target.loc["2023-10-22":"2024-04-15"] = 1.0
    
    # Rule 14: Oct 1, 2024 to Feb 15, 2025
    target.loc["2024-10-01":"2025-02-15"] = 1.0
    
    # Rule 17: Apr 20, 2025 to Oct 23, 2025
    target.loc["2025-04-20":"2025-10-23"] = 1.0
    
    # 20 Dec 2018 to 1 Mar 2019: No trade (0.0)
    target.loc["2018-12-20":"2019-03-01"] = 0.0
    
    # Noise dates: Sept 22, 2017 (no cut loss, should be 1.0)
    target.loc["2017-09-22"] = 1.0
    # Jan 9 and 11, 2018: Exit early, so should be 0.0 or 1.0?
    target.loc["2018-01-09":"2018-01-11"] = 0.0
    
    return target

# List of critical periods to check accuracy
critical_periods = [
    ("2017-01-01", "2017-01-25", "No-trade early Jan 2017"),
    ("2017-07-29", "2018-01-08", "Trade late 2017"),
    ("2018-01-09", "2018-01-11", "Exit Jan 2018 top"),
    ("2018-12-20", "2019-03-01", "No-trade bottom 2018-2019"),
    ("2020-01-10", "2020-03-04", "Trade early 2020"),
    ("2020-03-16", "2021-04-27", "Trade bull 2020-2021"),
    ("2021-07-23", "2021-11-28", "Trade late 2021"),
    ("2023-10-22", "2024-04-15", "Trade bull 2023-2024"),
    ("2024-10-01", "2025-02-15", "Trade late 2024")
]

try:
    df = load_data()
    # Slice to backtest range
    df = df.loc["2017-01-01":"2025-01-01"]
    target = get_user_target_exposure(df.index)
    
    df["target"] = target
    df["mismatch"] = df["target_exposure"] != df["target"]
    
    print(f"Total mismatch days: {df['mismatch'].sum()} out of {len(df)}")
    print(f"Accuracy: {(1 - df['mismatch'].sum()/len(df))*100:.2f}%")
    
    print("\n--- Detailed mismatches by rule periods ---")
    total_mis = 0
    total_days = 0
    for start, end, desc in critical_periods:
        sub = df.loc[start:end]
        if len(sub) > 0:
            mis = (sub["target_exposure"] != sub["target"]).sum()
            total_mis += mis
            total_days += len(sub)
            print(f"  {start} to {end} ({desc}): {mis}/{len(sub)} mismatched (Avg Exp: {sub['target_exposure'].mean():.2f})")
    print(f"Critical Periods Accuracy: {(1 - total_mis/total_days)*100:.2f}% ({total_mis}/{total_days} mismatch)")
except Exception as e:
    print(f"Error: {e}")
