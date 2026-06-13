import sqlite3
import pandas as pd
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend

conn = sqlite3.connect("database/lttd.db")
df_ohlcv = pd.read_sql("SELECT timestamp as date, open, high, low, close, volume FROM ohlcv", conn).drop_duplicates("date").set_index("date")
df_ohlcv.index = pd.to_datetime(df_ohlcv.index)
df_ohlcv = df_ohlcv.sort_index()

fourier = AdaptiveFourierSupertrend(dynamic_lookback=200)
res = fourier.compute(df_ohlcv)
print("static lookback 200 - NaNs:", res.isna().sum())
print("0.0s:", (res == 0.0).sum())
print("1.0s:", (res == 1.0).sum())

# Try dynamic_lookback as pd.Series
dl = pd.Series(200, index=df_ohlcv.index)
fourier2 = AdaptiveFourierSupertrend(dynamic_lookback=dl)
res2 = fourier2.compute(df_ohlcv)
print("\npd.Series lookback - NaNs:", res2.isna().sum())
print("0.0s:", (res2 == 0.0).sum())
print("1.0s:", (res2 == 1.0).sum())
