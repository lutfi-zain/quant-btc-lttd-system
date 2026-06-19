import sqlite3
import pandas as pd

conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT date, regime, posterior_prob FROM daily_lttd ORDER BY date", conn)
conn.close()

df["date"] = pd.to_datetime(df["date"])
df["regime_shifted"] = df["regime"].shift(1)
transitions = df[df["regime"] != df["regime_shifted"]]

print(f"Total rows in DB: {len(df)}")
print(f"Total transitions: {len(transitions) - 1}") # subtract the first row initialization

# Calculate average duration of each regime segment
df["segment_id"] = (df["regime"] != df["regime"].shift()).cumsum()
lengths = df.groupby("segment_id").size()
print(f"Mean segment duration: {lengths.mean():.2f} days")
print(f"Median segment duration: {lengths.median():.1f} days")
print(f"Max segment duration: {lengths.max()} days")
print(f"Min segment duration: {lengths.min()} days")

# Print first 20 transitions
print("\nFirst 20 transitions:")
print(transitions.head(21))

# Check transitions distribution
print("\nTransition counts by target regime:")
print(df.groupby("segment_id")["regime"].first().value_counts())
