import sqlite3
import pandas as pd
import numpy as np
import os, sys

def main():
    from tmp.test_ma_filter import load_data, simulate_with_ma_filter, calculate_metrics
    df = load_data()
    df = df.iloc[52:]
    
    params = {
        "entry_p": 8,
        "exit_p": 4,
        "score_entry": 0.435160,
        "score_exit": 0.294856,
        "cb_activate": -3.386067,
        "cb_cooloff": 0.789564,
        "rco_days": 3,
        "mhp_days": 12
    }
    
    exp_base = simulate_with_ma_filter(df, params, use_ma_filter=False)
    exp_ma = simulate_with_ma_filter(df, params, use_ma_filter=True, ma_period=150)
    
    df_2022 = df.loc['2022-01-01':'2022-12-31'].copy()
    
    # Base
    df_2022['pos_base'] = exp_base[df.index.get_loc('2022-01-01'):df.index.get_loc('2022-12-31')+1]
    df_2022['prev_pos_base'] = df_2022['pos_base'].shift(1).fillna(0.0)
    
    # MA-150
    df_2022['pos_ma'] = exp_ma[df.index.get_loc('2022-01-01'):df.index.get_loc('2022-12-31')+1]
    df_2022['prev_pos_ma'] = df_2022['pos_ma'].shift(1).fillna(0.0)
    
    print("Baseline 2022 transitions:")
    for idx, row in df_2022.iterrows():
        if row['pos_base'] != row['prev_pos_base']:
            print(f"  {idx.strftime('%Y-%m-%d')}: changed to {row['pos_base']} | close=${row['close']:,.2f}")
            
    print("\nMA-150 2022 transitions:")
    for idx, row in df_2022.iterrows():
        if row['pos_ma'] != row['prev_pos_ma']:
            print(f"  {idx.strftime('%Y-%m-%d')}: changed to {row['pos_ma']} | close=${row['close']:,.2f}")

if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
    main()
