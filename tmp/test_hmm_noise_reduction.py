import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from hmmlearn import hmm
from sklearn.cluster import KMeans

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.regime.hmm import train_hmm, infer_regime
from src.regime.features import prepare_features_df, prepare_features

# Load historical close prices
conn = sqlite3.connect("database/lttd.db")
df = pd.read_sql("SELECT timestamp, close FROM ohlcv ORDER BY timestamp", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)
close = df["close"]

# We will run the evaluation on the last 1000 days of the dataset to be fast but representative
eval_dates = df.index[-1000:]
print(f"Evaluating noise reduction methods over {len(eval_dates)} days ({eval_dates[0].date()} to {eval_dates[-1].date()})")

# Helper to calculate regime statistics
def get_stats(regimes, dates):
    df_reg = pd.DataFrame({"regime": regimes}, index=dates)
    df_reg["regime_shifted"] = df_reg["regime"].shift(1)
    transitions = len(df_reg[df_reg["regime"] != df_reg["regime_shifted"]]) - 1
    
    lengths = df_reg.groupby((df_reg["regime"] != df_reg["regime"].shift()).cumsum()).size()
    return {
        "transitions": transitions,
        "mean_segment": lengths.mean(),
        "median_segment": lengths.median(),
        "min_segment": lengths.min(),
        "max_segment": lengths.max()
    }

# ----------------- Method 1: Daily Retrain (Baseline) -----------------
print("\nRunning Method 1: Daily Retrain (Baseline)...")
baseline_regimes = []
for t in eval_dates:
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    
    model, mapping = train_hmm(close_train, window=21)
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    baseline_regimes.append(res["regime"])
    
stats_baseline = get_stats(baseline_regimes, eval_dates)
print("Baseline Stats:", stats_baseline)

# ----------------- Method 2: Retrain every 30 days (Monthly Refit) -----------------
print("\nRunning Method 2: Monthly Refit (Retrain every 30 days)...")
monthly_regimes = []
model = None
mapping = None

for i, t in enumerate(eval_dates):
    if i % 30 == 0 or model is None:
        train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
        close_train = close.loc[train_idx]
        model, mapping = train_hmm(close_train, window=21)
        
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    monthly_regimes.append(res["regime"])
    
stats_monthly = get_stats(monthly_regimes, eval_dates)
print("Monthly Refit Stats:", stats_monthly)

# ----------------- Method 3: Retrain every 90 days (Quarterly Refit) -----------------
print("\nRunning Method 3: Quarterly Refit (Retrain every 90 days)...")
quarterly_regimes = []
model = None
mapping = None

for i, t in enumerate(eval_dates):
    if i % 90 == 0 or model is None:
        train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
        close_train = close.loc[train_idx]
        model, mapping = train_hmm(close_train, window=21)
        
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    quarterly_regimes.append(res["regime"])
    
stats_quarterly = get_stats(quarterly_regimes, eval_dates)
print("Quarterly Refit Stats:", stats_quarterly)

# ----------------- Method 4: Daily Retrain + Posterior Smoothing (EMA) -----------------
print("\nRunning Method 4: Daily Retrain + Posterior Smoothing (EMA)...")
# We need to collect raw posteriors for all days and smooth them causally
raw_posteriors = []
for t in eval_dates:
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    
    model, mapping = train_hmm(close_train, window=21)
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    raw_posteriors.append(res["posteriors"])
    
# Convert list of dicts to DataFrame
df_post = pd.DataFrame(raw_posteriors, index=eval_dates)

for span in [5, 10, 20]:
    smoothed_post = df_post.ewm(span=span, adjust=False).mean()
    smoothed_regimes = smoothed_post.idxmax(axis=1).tolist()
    stats_smooth = get_stats(smoothed_regimes, eval_dates)
    print(f"EMA Posterior Smoothing (span={span}) Stats:", stats_smooth)

# ----------------- Method 5: Monthly Refit + Posterior Smoothing (EMA) -----------------
print("\nRunning Method 5: Monthly Refit + Posterior Smoothing (EMA)...")
monthly_posteriors = []
model = None
mapping = None

for i, t in enumerate(eval_dates):
    if i % 30 == 0 or model is None:
        train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
        close_train = close.loc[train_idx]
        model, mapping = train_hmm(close_train, window=21)
        
    res = infer_regime(model, mapping, close.loc[:t], window=21)
    monthly_posteriors.append(res["posteriors"])

df_monthly_post = pd.DataFrame(monthly_posteriors, index=eval_dates)
for span in [5, 10, 20]:
    smoothed_monthly_post = df_monthly_post.ewm(span=span, adjust=False).mean()
    smoothed_monthly_regimes = smoothed_monthly_post.idxmax(axis=1).tolist()
    stats_smooth_monthly = get_stats(smoothed_monthly_regimes, eval_dates)
    print(f"Monthly Refit + EMA Posterior Smoothing (span={span}) Stats:", stats_smooth_monthly)

# ----------------- Method 6: Feature Smoothing (SuperSmoother / EMA) -----------------
print("\nRunning Method 6: Feature Smoothing...")
# Modify how prepare_features works temporarily to see if smoothing features helps
# We will smooth log_returns and volatility before training and inference
# Ehlers SuperSmoother implementation
def super_smoother_series(series: pd.Series, period: int) -> pd.Series:
    if len(series) < 2:
        return series
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    values = series.values
    out = np.zeros_like(values)
    out[0] = values[0]
    out[1] = values[1]
    for t in range(2, len(values)):
        out[t] = c1 * (values[t] + values[t-1]) / 2.0 + c2 * out[t-1] + c3 * out[t-2]
    return pd.Series(out, index=series.index)

def prepare_smoothed_features_df(close: pd.Series, window: int = 21, smooth_period: int = 10) -> pd.DataFrame:
    log_returns = np.log(close / close.shift(1))
    vol = log_returns.rolling(window=window).std()
    sma200 = close.rolling(window=200).mean()
    sma_dist = (close - sma200) / sma200
    
    # Smooth log_returns and realized_volatility
    log_returns_smooth = super_smoother_series(log_returns.fillna(0.0), smooth_period)
    vol_smooth = super_smoother_series(vol.fillna(0.0), smooth_period)
    
    df = pd.DataFrame({
        "log_returns": log_returns_smooth,
        "realized_volatility": vol_smooth,
        "sma_dist": sma_dist
    })
    df.dropna(inplace=True)
    return df

# Let's override the features module locally and run daily training to see
def train_hmm_smoothed(close: pd.Series, window: int = 21, smooth_period: int = 10):
    features_df = prepare_smoothed_features_df(close, window=window, smooth_period=smooth_period)
    if len(features_df) < 200:
        raise ValueError("Insufficient data")
    features = features_df.values
    model = hmm.GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(features)
    means = np.zeros((3, 3))
    covars = np.zeros((3, 3))
    for i in range(3):
        cluster_data = features[labels == i]
        if len(cluster_data) > 0:
            means[i] = cluster_data.mean(axis=0)
            covars[i] = cluster_data.var(axis=0)
        else:
            means[i] = features.mean(axis=0)
            covars[i] = features.var(axis=0)
    covars = np.clip(covars, a_min=1e-6, a_max=None)
    model.means_ = means
    model.covars_ = covars
    model.init_params = "st"
    model.fit(features)
    means_ = model.means_
    bull_idx = int(np.argmax(means_[:, 2]))
    remaining = [i for i in [0, 1, 2] if i != bull_idx]
    if means_[remaining[0], 2] < means_[remaining[1], 2]:
        bear_idx = remaining[0]
        sideways_idx = remaining[1]
    else:
        bear_idx = remaining[1]
        sideways_idx = remaining[0]
    state_to_regime = {bull_idx: "BULL", bear_idx: "BEAR", sideways_idx: "SIDEWAYS"}
    return model, state_to_regime

def infer_regime_smoothed(model, state_to_regime, close, window=21, smooth_period=10):
    features_df = prepare_smoothed_features_df(close, window=window, smooth_period=smooth_period)
    features = features_df.values
    if len(features) > 1095:
        features = features[-1095:]
    proba = model.predict_proba(features)
    latest_proba = proba[-1]
    posteriors = {state_to_regime[i]: float(latest_proba[i]) for i in range(3)}
    regime = max(posteriors, key=posteriors.get)
    return {"regime": regime, "posteriors": posteriors}

print("\nRunning Method 6: Feature Smoothing (SuperSmoother-10)...")
smooth_features_regimes = []
for t in eval_dates:
    train_idx = df.index[(df.index >= t - pd.Timedelta(days=1095)) & (df.index < t)]
    close_train = close.loc[train_idx]
    
    model, mapping = train_hmm_smoothed(close_train, window=21, smooth_period=10)
    res = infer_regime_smoothed(model, mapping, close.loc[:t], window=21, smooth_period=10)
    smooth_features_regimes.append(res["regime"])
    
stats_smooth_features = get_stats(smooth_features_regimes, eval_dates)
print("Feature Smoothing (SuperSmoother-10) Stats:", stats_smooth_features)
