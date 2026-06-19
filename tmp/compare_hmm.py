import sqlite3
import pandas as pd
import numpy as np
from src.regime.hmm import train_hmm, infer_regime_history, infer_regime

# Load historical close prices
conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)
close = df["close"]

# Let's train a single static HMM model on the whole dataset
print("Training static HMM on full dataset...")
static_model, static_mapping = train_hmm(close, window=21)
df_static = infer_regime_history(static_model, static_mapping, close, window=21)

# Let's calculate the transitions for static HMM
df_static["regime_shifted"] = df_static["regime"].shift(1)
static_transitions = df_static[df_static["regime"] != df_static["regime_shifted"]]
print(f"Static HMM total rows: {len(df_static)}")
print(f"Static HMM total transitions: {len(static_transitions) - 1}")
static_lengths = df_static.groupby((df_static["regime"] != df_static["regime"].shift()).cumsum()).size()
print(f"Static HMM mean segment duration: {static_lengths.mean():.2f} days")
print(f"Static HMM median segment duration: {static_lengths.median():.1f} days")
print(f"Static HMM min segment duration: {static_lengths.min()} days")

# Let's simulate a rolling HMM (without parallelizing, just a subset to compare)
print("\nSimulating rolling HMM on last 500 days...")
rolling_regimes = []
dates = df.index[-500:]

for idx, t in enumerate(dates):
    # Segment into trailing 3-year history
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    
    # Train
    model, mapping = train_hmm(close_train, window=21)
    
    # Infer for latest day
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    rolling_regimes.append(res["regime"])

df_roll_compare = pd.DataFrame({"regime": rolling_regimes}, index=dates)
df_roll_compare["regime_shifted"] = df_roll_compare["regime"].shift(1)
roll_transitions = df_roll_compare[df_roll_compare["regime"] != df_roll_compare["regime_shifted"]]
print(f"Rolling HMM total transitions (last 500 days): {len(roll_transitions) - 1}")
roll_lengths = df_roll_compare.groupby((df_roll_compare["regime"] != df_roll_compare["regime"].shift()).cumsum()).size()
print(f"Rolling HMM mean segment: {roll_lengths.mean():.2f} days, median: {roll_lengths.median():.1f} days")

# For same 500 days, what is static HMM?
df_static_sub = df_static.loc[dates]
df_static_sub["regime_shifted"] = df_static_sub["regime"].shift(1)
static_sub_transitions = df_static_sub[df_static_sub["regime"] != df_static_sub["regime_shifted"]]
print(f"Static HMM total transitions (last 500 days): {len(static_sub_transitions) - 1}")
static_sub_lengths = df_static_sub.groupby((df_static_sub["regime"] != df_static_sub["regime"].shift()).cumsum()).size()
print(f"Static HMM mean segment (last 500 days): {static_sub_lengths.mean():.2f} days, median: {static_sub_lengths.median():.1f} days")
