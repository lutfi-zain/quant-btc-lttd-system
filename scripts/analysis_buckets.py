import sqlite3
import pandas as pd
import numpy as np

# Connect to database
conn = sqlite3.connect('database/lttd.db')

# Load LTTD target exposure and scores
df_lttd = pd.read_sql('SELECT data_as_of as date, final_score, target_exposure FROM daily_lttd ORDER BY date', conn)
df_ohlcv = pd.read_sql('SELECT timestamp as date, close FROM ohlcv ORDER BY date', conn)

df_lttd['date'] = pd.to_datetime(df_lttd['date']).dt.normalize()
df_ohlcv['date'] = pd.to_datetime(df_ohlcv['date']).dt.normalize()

df = pd.merge(df_lttd, df_ohlcv, on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

df['return'] = df['close'].pct_change().shift(-1).fillna(0) # Forward return to match signal of current day to next day's return

# Bin the final_score
bins = [-1.0, -0.5, 0.0, 0.5, 1.0]
df['score_bin'] = pd.cut(df['final_score'], bins=bins, include_lowest=True)

print("Average Daily Forward Return by Score Bin:")
print(df.groupby('score_bin')['return'].mean() * 100) # In %

print("\nCount of Days by Score Bin:")
print(df.groupby('score_bin')['return'].count())

# Missing out on compounded returns when score is slightly negative
df['continuous_exp'] = 0.5 + 0.5 * df['final_score']
df['binary_exp'] = np.where(df['final_score'] > 0, 1.0, 0.0)

# What is the total compounded return missed in each bin?
print("\nSum of Log Returns captured in each bin:")
df['log_ret'] = np.log1p(df['return'])
print("Buy & Hold Log Returns:")
print(df.groupby('score_bin')['log_ret'].sum())

print("\nBinary Log Returns:")
df['bin_log_ret'] = df['binary_exp'] * df['log_ret']
print(df.groupby('score_bin')['bin_log_ret'].sum())

print("\nContinuous Log Returns:")
df['cont_log_ret'] = df['continuous_exp'] * df['log_ret']
print(df.groupby('score_bin')['cont_log_ret'].sum())

