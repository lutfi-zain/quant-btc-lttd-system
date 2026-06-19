#!/usr/bin/env python3
import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.execution.sizing import (
    calculate_target_exposure,
    super_smoother,
    SUPERSMOOTHER_PERIOD_ENTRY,
    SUPERSMOOTHER_PERIOD_EXIT,
    MA_PERIOD,
    USE_MA_FILTER,
)
from src.data.valuation_api_client import ValuationApiClient
from tmp.evaluate_baseline_correct import calculate_metrics_react

def main():
    db_path = "database/lttd.db"
    conn = sqlite3.connect(db_path)
    
    # Load daily_lttd
    df_lttd = pd.read_sql("SELECT date, regime, final_score FROM daily_lttd ORDER BY date", conn)
    
    # Load ohlcv
    ohlcv_df = pd.read_sql("SELECT DATE(timestamp) as date, close FROM ohlcv ORDER BY timestamp", conn, parse_dates=["date"])
    ohlcv_df.set_index("date", inplace=True)
    conn.close()
    
    df_lttd["date_dt"] = pd.to_datetime(df_lttd["date"])
    df_lttd.set_index("date_dt", inplace=True)
    df_lttd = df_lttd.join(ohlcv_df[["close"]], how="inner")
    
    # SuperSmoother
    raw_scores = df_lttd["final_score"].values
    scores_series = pd.Series(raw_scores, index=df_lttd.index)
    smoothed_entry_list = super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_ENTRY).tolist()
    smoothed_exit_list = super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_EXIT).tolist()
    
    # Rolling MA
    ma_series = ohlcv_df["close"].rolling(MA_PERIOD).mean()
    
    valuation_client = ValuationApiClient()
    valuation_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    
    prev_exposure = 0.0
    prev_cb = False
    days_since_exit = 999
    days_in_position = 0
    
    updated_records = []
    
    for i in range(len(df_lttd)):
        date_str = df_lttd["date"].iloc[i]
        t_date = df_lttd.index[i]
        
        smoothed_score_entry = float(smoothed_entry_list[i])
        smoothed_score_exit = float(smoothed_exit_list[i])
        
        if prev_exposure >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
        composite_value = valuation_client.get_composite_value_for_date(t_date)
        price = float(df_lttd["close"].iloc[i])
        ma_val = float(ma_series.loc[t_date]) if (USE_MA_FILTER and not pd.isna(ma_series.loc[t_date])) else None
        
        exposure, cb_active = calculate_target_exposure(
            smoothed_score_entry=smoothed_score_entry,
            smoothed_score_exit=smoothed_score_exit,
            vol=0.0,
            regime=df_lttd["regime"].iloc[i],
            prev_exposure=prev_exposure,
            composite_value=composite_value,
            prev_circuit_breaker_active=prev_cb,
            days_since_exit=days_since_exit,
            days_in_position=days_in_position,
            price=price,
            ma_val=ma_val
        )
        
        updated_records.append((exposure, int(cb_active), date_str))
        prev_exposure = exposure
        prev_cb = cb_active
        
    # Write back to DB
    print("Writing new exposures back to database...")
    conn = sqlite3.connect(db_path)
    conn.executemany("""
        UPDATE daily_lttd
        SET target_exposure = ?, circuit_breaker_active = ?
        WHERE date = ?
    """, updated_records)
    conn.commit()
    conn.close()
    
    # Reload exposures to calculate metrics
    conn = sqlite3.connect(db_path)
    df_new = pd.read_sql("SELECT date, regime, final_score, target_exposure, close FROM daily_lttd d JOIN ohlcv o ON DATE(o.timestamp) = d.date ORDER BY d.date", conn, parse_dates=["date"])
    conn.close()
    df_new.set_index("date", inplace=True)
    
    exps = df_new["target_exposure"].values
    metrics = calculate_metrics_react(df_new, exps)
    
    print("\n--- NEW RE-CALCULATED METRICS ---")
    for k, v in metrics.items():
        print(f"  {k:16}: {v:.4f}" if isinstance(v, float) else f"  {k:16}: {v}")

if __name__ == "__main__":
    main()
