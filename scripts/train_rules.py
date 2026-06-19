import sqlite3
import pandas as pd
import numpy as np
from src.data.valuation_api_client import ValuationApiClient
from sklearn.tree import DecisionTreeRegressor, export_text

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score as score, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn)
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
    
    df["target_pct"] = 0.0
    last_pct = 0.0
    for t in df.index:
        if t in target_df.index:
            action = target_df.loc[t, "Action"]
            pct = target_df.loc[t, "EquityPct"]
            if action == "SELL" and pct == 100:
                last_pct = 0.0
            elif pct == 100:
                last_pct = 1.0
            elif pct == 50:
                last_pct = 0.5
        df.loc[t, "target_pct"] = last_pct
        
    # Features
    df["regime_bear"] = (df["regime"] == "BEAR").astype(int)
    df["regime_bull"] = (df["regime"] == "BULL").astype(int)
    
    X = df[["score", "composite_value", "regime_bear", "regime_bull"]].fillna(0)
    y = df["target_pct"]
    
    dt = DecisionTreeRegressor(max_depth=4)
    dt.fit(X, y)
    
    print("Decision Tree Rules:")
    print(export_text(dt, feature_names=list(X.columns)))
    
if __name__ == "__main__":
    main()
