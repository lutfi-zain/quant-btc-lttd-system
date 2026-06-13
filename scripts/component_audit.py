import os
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

def main():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/lttd.db"))
    conn = sqlite3.connect(db_path)
    
    # 1. Load data
    df_daily = pd.read_sql("SELECT date, final_score, regime FROM daily_lttd", conn, parse_dates=["date"]).set_index("date")
    df_ohlcv = pd.read_sql("SELECT SUBSTR(timestamp, 1, 10) as date, close FROM ohlcv", conn).drop_duplicates(subset=["date"])
    df_ohlcv["date"] = pd.to_datetime(df_ohlcv["date"])
    df_ohlcv = df_ohlcv.set_index("date")
    
    df_ind = pd.read_sql("SELECT date, indicator_name, score FROM indicator_scores", conn, parse_dates=["date"])
    df_ind_pivot = df_ind.pivot(index="date", columns="indicator_name", values="score")
    
    df = df_daily.join(df_ind_pivot, how="inner").join(df_ohlcv, how="inner").sort_index()
    
    # Define indicators
    indicators = df_ind_pivot.columns.tolist()
    
    print("=== LTTD Component Statistical Audit ===\n")
    print(f"Data Range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')} ({len(df)} days)\n")
    
    # 2. Distribution & Bounds
    print("--- 1. Distribution & Bounds ---")
    desc = df[indicators + ["final_score"]].describe(percentiles=[0.01, 0.5, 0.99]).T
    desc = desc[["min", "1%", "50%", "99%", "max", "mean", "std"]]
    print(desc.round(3).to_string())
    print("\n")
    
    # 3. Component Coherence (Correlation Matrix)
    print("--- 2. Inter-Component Coherence (Spearman Correlation) ---")
    corr = df[indicators + ["final_score"]].corr(method="spearman")
    print(corr.round(2).to_string())
    print("\n")
    
    # 4. Alignment with Final Score
    # What % of the time does the component have the same sign as the final score?
    print("--- 3. Directional Alignment with Final Score ---")
    alignments = {}
    for ind in indicators:
        # Sign agreement: both > 0 or both < 0
        agreement = np.sign(df[ind]) == np.sign(df["final_score"])
        alignments[ind] = agreement.mean() * 100
        
    for ind, align in sorted(alignments.items(), key=lambda x: x[1], reverse=True):
        print(f"{ind:20s}: {align:.1f}% directional agreement")
    print("\n")
    
    # 5. Predictive Power (Information Coefficient - IC)
    # Forward Returns (7d, 30d)
    print("--- 4. Predictive Power (Information Coefficient) ---")
    df["fwd_ret_7d"] = df["close"].shift(-7) / df["close"] - 1
    df["fwd_ret_30d"] = df["close"].shift(-30) / df["close"] - 1
    
    ic_data = []
    for col in indicators + ["final_score"]:
        valid_7d = df[[col, "fwd_ret_7d"]].dropna()
        ic_7d, _ = stats.spearmanr(valid_7d[col], valid_7d["fwd_ret_7d"])
        
        valid_30d = df[[col, "fwd_ret_30d"]].dropna()
        ic_30d, _ = stats.spearmanr(valid_30d[col], valid_30d["fwd_ret_30d"])
        
        ic_data.append({"Component": col, "IC_7d": ic_7d, "IC_30d": ic_30d})
        
    df_ic = pd.DataFrame(ic_data).set_index("Component")
    print(df_ic.round(3).to_string())
    print("\nNote: Absolute IC > 0.05 is generally considered strong in quant finance.")
    print("\n")
    
    # 6. Regime Hit Rates
    print("--- 5. Regime Return Characteristics ---")
    # Average forward returns per regime
    regime_fwd = df.groupby("regime")[["fwd_ret_7d", "fwd_ret_30d"]].mean() * 100
    print("Average Forward Returns (%) by Regime:")
    print(regime_fwd.round(2).to_string())

if __name__ == "__main__":
    main()
