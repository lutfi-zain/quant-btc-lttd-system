import sqlite3
import pandas as pd
import numpy as np
from src.regime.hmm import train_hmm
from src.regime.features import prepare_features_df

# Load historical close prices
conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)
close = df["close"]

# Train model on the entire dataset to inspect parameters
model, state_to_regime = train_hmm(close, window=21)

print("State to Regime mapping:")
print(state_to_regime)
print("\nTransition matrix (transmat_):")
print(model.transmat_)
print("\nMeans:")
for i in range(3):
    print(f"State {i} ({state_to_regime[i]}): Log Returns Mean={model.means_[i, 0]:.6f}, Vol Mean={model.means_[i, 1]:.6f}, SMA Dist Mean={model.means_[i, 2]:.6f}")

print("\nCovariances:")
print(model.covars_)
