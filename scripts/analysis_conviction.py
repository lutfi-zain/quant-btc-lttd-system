import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('database/lttd.db')
df_lttd = pd.read_sql('SELECT data_as_of as date, final_score, target_exposure FROM daily_lttd ORDER BY date', conn)
df_ohlcv = pd.read_sql('SELECT timestamp as date, close FROM ohlcv ORDER BY date', conn)

df_lttd['date'] = pd.to_datetime(df_lttd['date']).dt.normalize()
df_ohlcv['date'] = pd.to_datetime(df_ohlcv['date']).dt.normalize()

df = pd.merge(df_lttd, df_ohlcv, on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

df['return'] = df['close'].pct_change().shift(-1).fillna(0) # Target forward return
df['final_score_shifted'] = df['final_score'] # Already predicting tomorrow

# Let's create more granular bins
bins = [-1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0]
df['score_bin'] = pd.cut(df['final_score'], bins=bins, include_lowest=True)

print("Average Daily Forward Return (Arithmetic) by Score Bin (%):")
print(df.groupby('score_bin')['return'].mean() * 100)

print("\nVolatility (Daily) by Score Bin (%):")
print(df.groupby('score_bin')['return'].std() * 100)

print("\nSharpe Ratio (Daily Ann. approx) by Score Bin:")
mean = df.groupby('score_bin')['return'].mean()
std = df.groupby('score_bin')['return'].std()
print((mean / std) * np.sqrt(365))

print("\nCount:")
print(df.groupby('score_bin')['return'].count())

