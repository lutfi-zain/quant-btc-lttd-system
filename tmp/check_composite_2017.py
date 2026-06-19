import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    # Load composite values
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is None:
        print("Valuation cache is None!")
        return
        
    val_df = val_df.copy()
    val_df["date"] = pd.to_datetime(val_df["date"])
    if val_df["date"].dt.tz is not None:
        val_df["date"] = val_df["date"].dt.tz_convert(None)
    val_df.set_index("date", inplace=True)
    
    df_2017 = val_df.loc['2017-05-01':'2017-12-31']
    print("Composite value summary for 2017:")
    print(df_2017["composite_value"].describe())
    
    print("\nSample composite values in 2017:")
    for idx, row in df_2017.iterrows():
        if idx.day in [1, 15]:
            print(f"{idx.strftime('%Y-%m-%d')}: composite_value={row['composite_value']:.6f}")
            
if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
