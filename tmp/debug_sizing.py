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

def main():
    conn = sqlite3.connect("database/lttd.db")
    df_lttd = pd.read_sql("SELECT date, regime, final_score, target_exposure FROM daily_lttd ORDER BY date", conn)
    
    # Load ohlcv starting from 2014 to calculate MA
    ohlcv_df = pd.read_sql("SELECT DATE(timestamp) as date, close FROM ohlcv ORDER BY timestamp", conn, parse_dates=["date"])
    ohlcv_df.set_index("date", inplace=True)
    conn.close()
    
    df_lttd["date_dt"] = pd.to_datetime(df_lttd["date"])
    df_lttd.set_index("date_dt", inplace=True)
    df_lttd = df_lttd.join(ohlcv_df[["close"]], how="inner")
    
    # SuperSmoother on final_score
    raw_scores = df_lttd["final_score"].values
    scores_series = pd.Series(raw_scores, index=df_lttd.index)
    smoothed_entry_list = super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_ENTRY).tolist()
    smoothed_exit_list = super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_EXIT).tolist()
    
    # Pre-calculate MA on ohlcv_df
    ma_series = ohlcv_df["close"].rolling(MA_PERIOD).mean()
    
    valuation_client = ValuationApiClient()
    valuation_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    
    # Let's run the loop up to 2018-05-10
    prev_exposure = 0.0
    prev_cb = False
    days_since_exit = 999
    days_in_position = 0
    
    print(f"USE_MA_FILTER: {USE_MA_FILTER} | MA_PERIOD: {MA_PERIOD}")
    
    for i in range(len(df_lttd)):
        date_str = df_lttd["date"].iloc[i]
        t_date = df_lttd.index[i]
        
        smoothed_score_entry = float(smoothed_entry_list[i])
        smoothed_score_exit = float(smoothed_exit_list[i])
        
        # Track timers
        if prev_exposure >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
        composite_value = valuation_client.get_composite_value_for_date(t_date)
        price = float(df_lttd["close"].iloc[i])
        
        # Locate ma_val
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
        
        if date_str == "2018-05-10":
            print(f"\n--- DETAILED EVALUATION ON 2018-05-10 ---")
            print(f"  smoothed_score_entry : {smoothed_score_entry:.6f}")
            print(f"  smoothed_score_exit  : {smoothed_score_exit:.6f}")
            print(f"  prev_exposure        : {prev_exposure}")
            print(f"  composite_value      : {composite_value}")
            print(f"  prev_cb              : {prev_cb}")
            print(f"  days_since_exit      : {days_since_exit}")
            print(f"  price                : {price}")
            print(f"  ma_val               : {ma_val}")
            print(f"  price > ma_val       : {price > ma_val if ma_val else None}")
            print(f"  OUTPUT exposure      : {exposure}")
            print(f"  OUTPUT cb_active     : {cb_active}")
            print(f"  DB target_exposure   : {df_lttd['target_exposure'].iloc[i]}")
            break
            
        prev_exposure = exposure
        prev_cb = cb_active

if __name__ == "__main__":
    main()
