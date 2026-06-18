import sqlite3
import pandas as pd
import numpy as np
import random
import time
import os
from tqdm import tqdm
from joblib import Parallel, delayed

from src.features.ou_calibration import estimate_ou_halflife
from src.features.builder import FeatureMatrixBuilder
from src.ensemble.model import PCAConsensusEnsemble
from src.execution.sizing import calculate_target_exposure

from src.data.brk_ingestion_service import BRKIngestionService

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    ohlcv = pd.read_sql("SELECT * FROM ohlcv", conn)
    ohlcv["timestamp"] = pd.to_datetime(ohlcv["timestamp"], utc=True)
    ohlcv.set_index("timestamp", inplace=True)
    ohlcv.sort_index(inplace=True)
    
    cache_file = "database/onchain_cache.csv"
    if os.path.exists(cache_file):
        onchain = pd.read_csv(cache_file, index_col=0)
        onchain.index = pd.to_datetime(onchain.index, utc=True)
    else:
        for attempt in range(3):
            try:
                ingestion = BRKIngestionService()
                onchain = ingestion.fetch_historical(lookback_days=4500)
                onchain.to_csv(cache_file)
                break
            except Exception as e:
                print(f"Fetch failed: {e}. Retrying...")
                time.sleep(5)
                
    # Pre-load HMM regime from the database so we can accurately simulate the real pipeline
    daily_lttd = pd.read_sql("SELECT date, regime FROM daily_lttd", conn)
    daily_lttd["timestamp"] = pd.to_datetime(daily_lttd["date"], utc=True)
    daily_lttd.set_index("timestamp", inplace=True)
    daily_lttd.drop(columns=["date"], inplace=True)
    
    return ohlcv, onchain, daily_lttd

def run_single_simulation(params, ohlcv, onchain, daily_lttd, dates):
    """
    Run one complete WFO simulation using the provided randomized parameters.
    """
    # 1. Initialize custom builder
    # To use custom params, we would need to modify FeatureMatrixBuilder to accept them, 
    # but for now we'll inject them into the objects directly.
    builder = FeatureMatrixBuilder()
    builder.rsi50.rsi_period = params["rsi_period"]
    builder.fourier_supertrend.multiplier = params["supertrend_multiplier"]
    builder.trend_strength.vwma_length = params["vwma_length"]
    builder.trend_strength.atr_length = params["atr_length"]
    builder.advanced_stochastic.default_lookback = params["stoch_lookback"]
    
    # 2. Build full feature matrix once to save time
    # (In true WFO we only have access to historical, but since indicators are causal, 
    # computing the matrix on the whole dataset is mathematically identical and 100x faster).
    from src.backtest.wfo import point_in_time_join
    df_merged = point_in_time_join(ohlcv, onchain)
    feature_matrix = builder.build_matrix(df_merged)
    
    # 3. WFO Simulation
    results = []
    
    tech_cols = ["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex"]
    
    # Drop NAs
    df_merged = df_merged.join(feature_matrix[tech_cols], how="inner").dropna()
    valid_dates = df_merged.index[df_merged.index >= pd.Timestamp("2016-01-01", tz="UTC")]
    
    if len(valid_dates) < 500:
        return {"sharpe": 0.0, "params": params}
    
    # Calculate returns for regime
    log_returns = np.log(df_merged["close"]).diff().fillna(0)
    realized_vol = log_returns.rolling(window=21).std() * np.sqrt(365)
    
    scores = np.zeros(len(valid_dates))
    regimes = ["SIDEWAYS"] * len(valid_dates)
    
    for i, t in enumerate(valid_dates):
        # 3-year trailing window
        train_start = t - pd.DateOffset(years=3)
        train_idx = df_merged.index[(df_merged.index >= train_start) & (df_merged.index < t)]
        
        if len(train_idx) < 250:
            continue
            
        X_train = df_merged.loc[train_idx, tech_cols]
        
        # PCA
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)
        
        pca = PCA(n_components=1)
        pca.fit(X_scaled)
        
        # Ensemble weights
        ensemble = PCAConsensusEnsemble()
        ensemble.fit(X_train, pca_components_matrix=pca.components_, kept_cols=tech_cols)
        
        # Current row
        X_t = df_merged.loc[[t], tech_cols]
        score_t = ensemble.predict(X_t).iloc[0]
        scores[i] = score_t
        
    # 4. Smoothing & Execution
    scores_series = pd.Series(scores, index=valid_dates)
    smoothed = scores_series.ewm(span=params["smoothing_span"], adjust=False).mean()
    
    exposure = np.zeros(len(valid_dates))
    current_exp = 0.0
    
    # We create a pseudo-sizing instance
    from src.execution.sizing import calculate_target_exposure
    
    for i in range(len(valid_dates)):
        dt = valid_dates[i]
        sc = smoothed.iloc[i]
        
        # Get HMM regime
        regime = daily_lttd.loc[dt, "regime"] if dt in daily_lttd.index else "SIDEWAYS"
        
        # Onchain metrics
        row = df_merged.loc[dt]
        onchain_dict = {
            "sth_mvrv": row.get("sth_mvrv", 0.0),
            "sth_nupl": row.get("sth_nupl", 0.0)
        }
        
        # In sizing.py, thresholds are hardcoded, but we want to simulate random thresholds
        # Let's inline the sizing logic so we can pass our custom params
        if regime == "BEAR":
            raw_exposure = 0.0
        else:
            raw_exposure = current_exp
            if current_exp >= 0.9:
                if sc <= params["exit_thresh"]:
                    raw_exposure = 0.0
            else:
                if sc >= params["enter_thresh"]:
                    raw_exposure = 1.0
                    
            if raw_exposure > 0:
                sth_nupl = onchain_dict.get("sth_nupl", 0.0)
                sth_mvrv = onchain_dict.get("sth_mvrv", 0.0)
                
                if sth_nupl > 0.75 or sth_mvrv > 2.0:
                    raw_exposure = 0.0
                elif sth_nupl > 0.60 or sth_mvrv > 1.5:
                    raw_exposure = min(raw_exposure, 0.50)
                    
        # Apply Volatility Scaling
        log_ret = log_returns.loc[dt]
        vol = realized_vol.loc[dt]
        
        # To strictly match backfill, we don't scale it further if calculate_target_exposure doesn't,
        # Wait, sizing.py doesn't do volatility scaling inside calculate_target_exposure anymore!
        # It's exactly the logic above.
        
        exposure[i] = raw_exposure
        current_exp = raw_exposure
        
    # 5. Evaluate Performance
    pos_series = pd.Series(exposure, index=valid_dates).shift(1).fillna(0)
    daily_returns = ohlcv["close"].pct_change().reindex(valid_dates).fillna(0)
    
    strat_returns = daily_returns * pos_series
    
    if strat_returns.std() == 0:
        sharpe = 0.0
        sortino = 0.0
    else:
        sharpe = np.sqrt(365) * (strat_returns.mean()) / strat_returns.std()
        downside_returns = strat_returns[strat_returns < 0]
        if downside_returns.std() == 0:
            sortino = 0.0
        else:
            sortino = np.sqrt(365) * (strat_returns.mean()) / downside_returns.std()
            
    # Calculate Win Rate at Trade Level
    # Find start and end of trades
    pos_shifted = pos_series.shift(1).fillna(0)
    in_pos = pos_series > 0
    starts = valid_dates[(in_pos) & (~in_pos.shift(1).fillna(False))].tolist()
    ends = valid_dates[(~in_pos) & (in_pos.shift(1).fillna(False))].tolist()
    
    if len(starts) > len(ends):
        ends.append(valid_dates[-1])
        
    trades = []
    for s, e in zip(starts, ends):
        ret = (ohlcv.loc[e, "close"] - ohlcv.loc[s, "close"]) / ohlcv.loc[s, "close"]
        trades.append(ret)
        
    win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0.0
        
    return {
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": win_rate,
        "return": (1 + strat_returns).prod() - 1,
        "params": params
    }

def run_random_search(n_iterations=100):
    print(f"Starting Randomized WFO Parameter Search ({n_iterations} iterations)...")
    ohlcv, onchain, daily_lttd = load_data()
    dates = ohlcv.index[ohlcv.index >= pd.Timestamp("2016-01-01", tz="UTC")]
    
    param_grid = []
    for _ in range(n_iterations):
        p = {
            "rsi_period": random.randint(50, 300),
            "supertrend_multiplier": random.uniform(2.0, 5.0),
            "vwma_length": random.randint(50, 200),
            "atr_length": random.randint(14, 100),
            "stoch_lookback": random.randint(100, 300),
            "smoothing_span": random.choice([3, 5, 7, 9]),
            "enter_thresh": round(random.uniform(0.5, 0.8), 2),
            "exit_thresh": round(random.uniform(0.1, 0.45), 2),
        }
        param_grid.append(p)
        
    # Run in parallel to save time
    results = Parallel(n_jobs=-1)(
        delayed(run_single_simulation)(p, ohlcv, onchain, daily_lttd, dates) for p in tqdm(param_grid)
    )
    
    # Sort and save
    valid_results = [r for r in results if r["sharpe"] > 0]
    valid_results.sort(key=lambda x: x["sharpe"], reverse=True)
    
    df_res = pd.DataFrame([
        {
            "sharpe": r["sharpe"],
            "sortino": r["sortino"],
            "win_rate": r["win_rate"],
            "return": r["return"],
            **r["params"]
        }
        for r in valid_results
    ])
    
    df_res.to_csv("random_search_results.csv", index=False)
    print("\nTop 5 Results:")
    print(df_res.head(5).to_string())
    print("\nSaved all results to random_search_results.csv")

if __name__ == "__main__":
    run_random_search(200)
