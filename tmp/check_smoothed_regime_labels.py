import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from src.regime.hmm import train_hmm, infer_regime

conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)
close = df["close"]

eval_dates = df.index[-1000:]

print("Running HMM daily refit for eval period...")
raw_posteriors = []
for t in eval_dates:
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    model, mapping = train_hmm(close_train, window=21)
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    raw_posteriors.append(res["posteriors"])
    
df_post = pd.DataFrame(raw_posteriors, index=eval_dates)

def print_segments(name, regimes):
    df_seg = pd.DataFrame({"regime": regimes}, index=eval_dates)
    df_seg["segment_id"] = (df_seg["regime"] != df_seg["regime"].shift()).cumsum()
    
    print(f"\n--- Segments for {name} ---")
    segments = df_seg.groupby("segment_id")
    for seg_id, grp in segments:
        reg = grp["regime"].iloc[0]
        start_date = grp.index[0].strftime("%Y-%m-%d")
        end_date = grp.index[-1].strftime("%Y-%m-%d")
        duration = len(grp)
        print(f"  Segment {seg_id:2d}: {reg:<8} | {start_date} to {end_date} | Duration: {duration:3d} days")

# Check span=15
smoothed_15 = df_post.ewm(span=15, adjust=False).mean()
regimes_15 = smoothed_15.idxmax(axis=1).tolist()
print_segments("EMA span=15", regimes_15)

# Check span=20
smoothed_20 = df_post.ewm(span=20, adjust=False).mean()
regimes_20 = smoothed_20.idxmax(axis=1).tolist()
print_segments("EMA span=20", regimes_20)
