import os
import sys
import sqlite3
import pandas as pd
import numpy as np

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.regime.hmm import train_hmm, infer_regime
from src.regime.features import prepare_features_df

# Load historical close prices
conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)
close = df["close"]

eval_dates = df.index[-1000:]

# Get raw daily posteriors (daily retrain baseline)
print("Calculating raw posteriors for eval period...")
raw_posteriors = []
for t in eval_dates:
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    
    model, mapping = train_hmm(close_train, window=21)
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    raw_posteriors.append(res["posteriors"])
    
df_post = pd.DataFrame(raw_posteriors, index=eval_dates)

# Helper to calculate stats
def print_stats(name, regimes):
    df_reg = pd.DataFrame({"regime": regimes}, index=eval_dates)
    df_reg["regime_shifted"] = df_reg["regime"].shift(1)
    transitions = len(df_reg[df_reg["regime"] != df_reg["regime_shifted"]]) - 1
    lengths = df_reg.groupby((df_reg["regime"] != df_reg["regime"].shift()).cumsum()).size()
    print(f"{name:<45} | Transitions: {transitions:<4} | Mean: {lengths.mean():.1f}d | Median: {lengths.median():.1f}d | Min: {lengths.min()}d | Max: {lengths.max()}d")

# 1. Baseline: Argmax
argmax_regimes = df_post.idxmax(axis=1).tolist()
print_stats("Baseline (Argmax)", argmax_regimes)

# 2. Hysteresis Threshold Transition
for threshold in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
    hyst_regimes = []
    current_regime = argmax_regimes[0]
    hyst_regimes.append(current_regime)
    
    for i in range(1, len(df_post)):
        row = df_post.iloc[i]
        # Find candidate state (highest prob)
        candidate = row.idxmax()
        prob = row[candidate]
        
        if prob > threshold:
            current_regime = candidate
        
        hyst_regimes.append(current_regime)
        
    print_stats(f"Hysteresis (threshold={threshold})", hyst_regimes)

# 3. Smoothed Posterior Argmax (EMA span=10, 15, 20)
for span in [5, 10, 15, 20]:
    smoothed_post = df_post.ewm(span=span, adjust=False).mean()
    smoothed_regimes = smoothed_post.idxmax(axis=1).tolist()
    print_stats(f"EMA Smoothed Posteriors (span={span})", smoothed_regimes)
