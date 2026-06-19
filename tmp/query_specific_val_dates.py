import requests
import pandas as pd
import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

def main():
    from src.data.valuation_api_client import ValuationApiClient
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    
    val_df_processed = val_df.copy()
    val_df_processed["date"] = pd.to_datetime(val_df_processed["date"])
    if val_df_processed["date"].dt.tz is not None:
        val_df_processed["date"] = val_df_processed["date"].dt.tz_convert(None)
    val_df_processed.set_index("date", inplace=True)
    
    dates = ['2018-05-08', '2018-08-01', '2018-09-11']
    for d in dates:
        ts = pd.Timestamp(d)
        print(f"--- Around {d} ---")
        # print 5 rows before and after
        start = ts - pd.Timedelta(days=5)
        end = ts + pd.Timedelta(days=5)
        print(val_df_processed.loc[start:end, ['composite_value']])

if __name__ == '__main__':
    main()
