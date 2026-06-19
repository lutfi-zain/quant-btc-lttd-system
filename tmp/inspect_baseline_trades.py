#!/usr/bin/env python3
import sqlite3
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tmp.evaluate_baseline_correct import load_data, simulate_exposures

def main():
    df = load_data()
    
    baseline_params = {
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
    
    exposures = simulate_exposures(df, baseline_params)
    df["target_exposure"] = exposures
    
    # Run exact trade log extraction
    close = df["close"].values
    prevExposure = 0.0
    dailyReturns = []
    
    winTrades = 0
    totalTrades = 0
    currentTradeReturn = 0.0
    inTrade = False
    
    trades_log = []
    entry_idx = 0
    
    for i in range(len(df)):
        date_val = df.index[i]
        price = close[i]
        
        if i > 0:
            prev_close = close[i-1]
            btcDailyReturn = (price - prev_close) / prev_close
            stratReturn = prevExposure * btcDailyReturn
            dailyReturns.append(stratReturn)
            
            if inTrade:
                currentTradeReturn = (1.0 + currentTradeReturn) * (1.0 + stratReturn) - 1.0
                
        exposure = exposures[i]
        if exposure > 0.0 and prevExposure == 0.0:
            inTrade = True
            currentTradeReturn = 0.0
            entry_idx = i
            totalTrades += 1
        elif exposure == 0.0 and prevExposure > 0.0:
            inTrade = False
            is_win = currentTradeReturn > 0.0
            if is_win:
                winTrades += 1
            trades_log.append({
                "trade_num": len(trades_log) + 1,
                "entry_date": df.index[entry_idx].strftime("%Y-%m-%d"),
                "exit_date": date_val.strftime("%Y-%m-%d"),
                "duration_days": i - entry_idx,
                "return_pct": currentTradeReturn * 100.0,
                "status": "WIN" if is_win else "LOSS",
                "entry_price": close[entry_idx],
                "exit_price": price,
                "entry_score": df["final_score"].values[entry_idx],
                "exit_score": df["final_score"].values[i]
            })
            
        prevExposure = exposure
        
    print(f"\nTotal Trades calculated in loop: {totalTrades}")
    print(f"Win Trades: {winTrades}")
    print(f"Win Rate: {(winTrades / totalTrades) * 100.0:.2f}%")
    
    print("\n--- DETAILED TRADE LOG ---")
    log_df = pd.DataFrame(trades_log)
    print(log_df.to_string(index=False))
    
    # Find all losses
    losses = log_df[log_df["status"] == "LOSS"]
    print("\n--- LOSS DETAILS ---")
    print(losses.to_string(index=False))

if __name__ == "__main__":
    main()
