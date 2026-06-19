#!/usr/bin/env python3
import sqlite3
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def main():
    conn = sqlite3.connect("database/lttd.db")
    db_df = pd.read_sql("""
        SELECT date, regime, final_score, target_exposure, circuit_breaker_active 
        FROM daily_lttd 
        WHERE date BETWEEN '2018-05-01' AND '2018-05-15'
        ORDER BY date
    """, conn)
    conn.close()
    
    # Query composite values from Valuation API cache for these dates
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    
    val_df["date_str"] = pd.to_datetime(val_df["date"]).dt.strftime("%Y-%m-%d")
    val_subset = val_df[val_df["date_str"].between("2018-05-01", "2018-05-15")]
    
    print("--- DATABASE ROWS ---")
    print(db_df)
    
    print("\n--- VALUATION SYSTEM CACHE ---")
    print(val_subset[["date_str", "composite_value"]])

if __name__ == "__main__":
    main()
