import sqlite3
import pandas as pd
from src.data.valuation_api_client import ValuationApiClient

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("SELECT date, regime, final_score FROM daily_lttd", conn)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is not None:
        val_df["date"] = pd.to_datetime(val_df["date"]).dt.tz_convert(None)
        val_df.set_index("date", inplace=True)
        df = df.join(val_df, how="left")
        
    df["composite_value"] = df["composite_value"].fillna(0.0)
    
    target_df = pd.read_csv("docs/isps/isp-signals-btcusd-2026-06-13.csv")
    target_df["Date"] = pd.to_datetime(target_df["Date"])
    target_df.set_index("Date", inplace=True)
    
    print(f"{'Date':<15} | {'EqPct':<5} | {'Regime':<8} | {'Final Score':<12} | {'Composite':<10}")
    print("-" * 65)
    
    for t in target_df.index:
        t_str = t.strftime("%Y-%m-%d")
        if t in df.index:
            row = df.loc[t]
            tgt_pct = target_df.loc[t, "EquityPct"]
            print(f"{t_str:<15} | {tgt_pct:<5} | {row['regime']:<8} | {row['final_score']:<12.4f} | {row['composite_value']:<10.4f}")

if __name__ == "__main__":
    main()
