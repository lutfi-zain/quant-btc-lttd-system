#!/usr/bin/env python3
import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tmp.evaluate_baseline_correct import load_data, super_smoother

def main():
    df = load_data()
    
    params = {
        "entry_p": 8,
        "exit_p": 5,
        "score_entry": 0.3591637228998046,
        "score_exit": 0.32448227800286483,
        "cb_activate": -2.8290154952614124,
        "cb_cooloff": 0.7123354436183149,
        "rco_days": 4,
        "mhp_days": 12,
        "use_bear_override": False,
        "use_ma_filter": True,
        "ma_period": 229
    }
    
    smoothed_entry = super_smoother(df["final_score"], params["entry_p"]).values
    smoothed_exit = super_smoother(df["final_score"], params["exit_p"]).values
    ma_val_arr = df["close"].rolling(params["ma_period"]).mean().values
    
    close_val = df["close"].values
    regime_val = df["regime"].values
    comp_val = df["composite_value"].values
    
    exposures = np.zeros(len(df))
    cb_active = False
    prev_exp = 0.0
    days_since_exit = 999
    days_in_position = 0
    
    idx_2018 = df.index.get_loc("2018-05-10")
    
    # We will print variables from 5 days before to 2018-05-10
    start_idx = idx_2018 - 5
    for i in range(len(df)):
        score_ent = smoothed_entry[i]
        score_ex = smoothed_exit[i]
        comp = comp_val[i]
        regime = regime_val[i]
        price = close_val[i]
        ma_val = ma_val_arr[i]
        
        if prev_exp >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
        exp = prev_exp
        
        # Circuit Breaker
        if cb_active:
            if comp > params["cb_cooloff"]:
                cb_active = False
            else:
                exp = 0.0
        else:
            if comp <= params["cb_activate"]:
                cb_active = True
                exp = 0.0
                
        if not cb_active and comp > params["cb_activate"]:
            # Score based entry/exit
            if prev_exp >= 0.9:  # IN position
                if days_in_position < params["mhp_days"]:
                    exp = 1.0  # Force hold (MHP)
                else:
                    if score_ex <= params["score_exit"]:
                        exp = 0.0
            else:  # OUT position
                if days_since_exit >= params["rco_days"]:
                    ma_condition = True
                    if params["use_ma_filter"] and ma_val is not None and not np.isnan(ma_val):
                        ma_condition = (price > ma_val)
                        
                    if score_ent >= params["score_entry"] and ma_condition:
                        exp = 1.0
                
            # BEAR regime override
            if params["use_bear_override"] and regime == "BEAR":
                exp = 0.0
                
            # Deep value boost override
            if comp >= 2.000613 and exp == 0.0:
                if days_since_exit >= params["rco_days"]:
                    exp = 1.0
                
            # Binary enforcement
            exp = 1.0 if exp > 0.5 else 0.0
            
        if start_idx <= i <= idx_2018:
            print(f"Date: {df.index[i].strftime('%Y-%m-%d')} | Price: {price:.2f} | MA: {ma_val:.2f} | ScoreEnt: {score_ent:.4f} | DaysSinceExit: {days_since_exit} | prev_exp: {prev_exp} | exp: {exp} | cb_active: {cb_active}")
            
        exposures[i] = exp
        prev_exp = exp
        
if __name__ == "__main__":
    main()
