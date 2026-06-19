import pandas as pd
from src.data.brk_ingestion_service import BRKIngestionService
from src.data.pipeline import ohlcv_pipeline

brk = BRKIngestionService()
df_onchain = brk.fetch_historical(lookback_days=4000)
df_ohlcv = ohlcv_pipeline()

df_onchain.index = pd.to_datetime(df_onchain.index).tz_localize(None)
df_ohlcv.index = pd.to_datetime(df_ohlcv.index).tz_localize(None)

df = df_ohlcv.join(df_onchain, how="inner")

tops = [
    ("2017 Top", "2017-11-01", "2018-01-15"),
    ("2021 Spring Top", "2021-03-01", "2021-05-15"),
    ("2021 Fall Top", "2021-10-01", "2021-11-30"),
    ("2024 Spring Top", "2024-02-15", "2024-04-15")
]

for name, start, end in tops:
    mask = (df.index >= start) & (df.index <= end)
    top_window = df[mask]
    if not top_window.empty:
        max_close_idx = top_window["close"].idxmax()
        peak_row = top_window.loc[max_close_idx]
        
        max_mvrv = top_window["sth_mvrv"].max()
        max_nupl = top_window["sth_nupl"].max()
        
        print(f"=== {name} ===")
        print(f"Peak Price Date: {max_close_idx.strftime('%Y-%m-%d')} | Price: ${peak_row['close']:,.0f}")
        print(f"MVRV at Peak : {peak_row['sth_mvrv']:.2f} (Window Max: {max_mvrv:.2f})")
        print(f"NUPL at Peak : {peak_row['sth_nupl']:.2f} (Window Max: {max_nupl:.2f})")
        print("")
