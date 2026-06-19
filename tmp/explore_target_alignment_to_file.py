import sqlite3
import pandas as pd
import numpy as np
import os, sys

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
    
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is not None:
        val_df = val_df.copy()
        val_df["date"] = pd.to_datetime(val_df["date"])
        if val_df["date"].dt.tz is not None:
            val_df["date"] = val_df["date"].dt.tz_convert(None)
        val_df.set_index("date", inplace=True)
        df = df.join(val_df[["composite_value"]], how="left")
    df["composite_value"] = df["composite_value"].fillna(0.0)
    return df

def main():
    df = load_data()
    
    periods = [
        ("Jan 2017", "2017-01-01", "2017-01-25"),
        ("July-Aug 2017", "2017-07-20", "2017-08-25"),
        ("Sept 22, 2017", "2017-09-18", "2017-09-26"),
        ("Jan 2018", "2018-01-01", "2018-01-20"),
        ("Dec 2018 - Mar 2019", "2018-12-15", "2019-03-05"),
        ("Jan - Mar 2020", "2020-01-05", "2020-03-10"),
        ("Mar - Oct 2020", "2020-03-10", "2020-10-25"),
        ("Apr 2021", "2021-04-20", "2021-05-05"),
        ("July - Nov 2021", "2021-07-15", "2021-11-30"),
        ("Nov 2021 - Jan 2023", "2021-11-25", "2023-01-15"),
        ("July 2023", "2023-07-01", "2023-07-31"),
        ("Oct 2023", "2023-10-15", "2023-11-01"),
        ("Jan - Feb 2024", "2024-01-15", "2024-02-28"),
        ("Apr - Sept 2024", "2024-04-10", "2024-10-05"),
        ("Oct 2024 - Feb 2025", "2024-09-25", "2025-02-20"),
        ("Feb - Apr 2025", "2025-02-10", "2025-04-25"),
        ("Apr - Oct 2025", "2025-04-15", "2025-10-31"),
        ("Nov 2025 to Present", "2025-10-25", "2026-06-26")
    ]
    
    with open("tmp/explore_target_alignment.txt", "w") as f:
        f.write(f"Total rows: {len(df)}\n")
        for name, start, end in periods:
            sub = df.loc[start:end]
            if sub.empty:
                continue
            f.write(f"\n=== Period: {name} ({start} to {end}) ===\n")
            f.write(f"  Close range: {sub['close'].min():.1f} - {sub['close'].max():.1f}\n")
            f.write(f"  Regimes present: {sub['regime'].unique()}\n")
            f.write(f"  Final score range: {sub['final_score'].min():.4f} to {sub['final_score'].max():.4f}\n")
            f.write(f"  Composite range: {sub['composite_value'].min():.4f} to {sub['composite_value'].max():.4f}\n")
            diffs = sub["target_exposure"].diff().fillna(0.0) != 0
            changes = sub[diffs | (sub.index == sub.index[0]) | (sub.index == sub.index[-1])]
            f.write("  Key Exposure / State timeline:\n")
            for date, row in changes.iterrows():
                f.write(f"    {date.strftime('%Y-%m-%d')}: close={row['close']:8.1f} | regime={row['regime']:8} | score={row['final_score']:6.4f} | composite={row['composite_value']:6.4f} | exposure={row['target_exposure']:.1f}\n")

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
