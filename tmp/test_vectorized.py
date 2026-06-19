#!/usr/bin/env python3
import sqlite3
import numpy as np
import pandas as pd
import sys
import os

# Ensure parent directory is in Python path for importing ValuationApiClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def load_data():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn, parse_dates=["date"])
    conn.close()
    df.set_index("date", inplace=True)
    df["simple_return"] = df["close"].pct_change().fillna(0.0)
    return df

def calculate_metrics_exact(df, exposures):
    close = df["close"].values
    equity = 1.0
    btcHold = 1.0
    peakEquity = 1.0
    maxDrawdown = 0.0
    prevExposure = 0.0
    dailyReturns = []
    winTrades = 0
    totalTrades = 0
    currentTradeReturn = 0.0
    inTrade = False
    
    for i in range(1, len(df)):
        prev_close = close[i-1]
        price = close[i]
        btcDailyReturn = (price - prev_close) / prev_close
        btcHold = btcHold * (1.0 + btcDailyReturn)
        stratReturn = prevExposure * btcDailyReturn
        equity = equity * (1.0 + stratReturn)
        dailyReturns.append(stratReturn)
        if equity > peakEquity:
            peakEquity = equity
        drawdown = (peakEquity - equity) / peakEquity
        if drawdown > maxDrawdown:
            maxDrawdown = drawdown
        if inTrade:
            currentTradeReturn = (1.0 + currentTradeReturn) * (1.0 + stratReturn) - 1.0
        exposure = exposures[i]
        if exposure > 0.0 and prevExposure == 0.0:
            inTrade = True
            currentTradeReturn = 0.0
            totalTrades += 1
        elif exposure == 0.0 and prevExposure > 0.0:
            inTrade = False
            if currentTradeReturn > 0.0:
                winTrades += 1
        prevExposure = exposure
        
    days = len(dailyReturns)
    years = days / 365.25
    totalReturnPct = (equity - 1.0) * 100.0
    cagr = ((equity) ** (1.0 / (years or 1.0)) - 1.0) * 100.0 if equity > 0 else 0.0
    meanDailyReturn = sum(dailyReturns) / (days or 1)
    variance = sum((r - meanDailyReturn) ** 2 for r in dailyReturns) / (days or 1)
    stdDev = np.sqrt(variance)
    annualizedStdDev = stdDev * np.sqrt(365)
    negativeReturns = [r for r in dailyReturns if r < 0.0]
    downsideVariance = sum(r ** 2 for r in negativeReturns) / (days or 1) if negativeReturns else 0.0
    annualizedDownsideDev = np.sqrt(downsideVariance) * np.sqrt(365)
    sharpe = (meanDailyReturn * 365.0) / annualizedStdDev if annualizedStdDev > 0 else 0.0
    sortino = (meanDailyReturn * 365.0) / annualizedDownsideDev if annualizedDownsideDev > 0 else 0.0
    winRate = (winTrades / totalTrades) * 100.0 if totalTrades > 0 else 0.0
    
    return {
        "strategy_return": totalReturnPct,
        "cagr": cagr,
        "max_dd": maxDrawdown * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": winRate,
        "total_trades": totalTrades,
        "win_trades": winTrades
    }

def calculate_metrics_vectorized(df, exposures):
    close = df["close"].values
    btcDailyReturn = (close[1:] - close[:-1]) / close[:-1]
    # exposures[:-1] corresponds to prevExposure for each day from index 1 to len(df)-1
    stratReturn = exposures[:-1] * btcDailyReturn
    
    equity_curve = np.cumprod(1.0 + stratReturn)
    equity = equity_curve[-1]
    peakEquity = np.maximum.accumulate(equity_curve)
    maxDrawdown = np.max((peakEquity - equity_curve) / peakEquity)
    
    days = len(stratReturn)
    years = days / 365.25
    
    totalReturnPct = (equity - 1.0) * 100.0
    cagr = (equity ** (1.0 / years) - 1.0) * 100.0 if equity > 0 else 0.0
    
    meanDailyReturn = np.mean(stratReturn)
    stdDev = np.std(stratReturn)
    annualizedStdDev = stdDev * np.sqrt(365)
    
    negativeReturns = stratReturn[stratReturn < 0.0]
    downsideDev = np.sqrt(np.sum(negativeReturns ** 2) / days) if len(negativeReturns) > 0 else 0.0
    annualizedDownsideDev = downsideDev * np.sqrt(365)
    
    sharpe = (meanDailyReturn * 365.0) / annualizedStdDev if annualizedStdDev > 0 else 0.0
    sortino = (meanDailyReturn * 365.0) / annualizedDownsideDev if annualizedDownsideDev > 0 else 0.0
    
    # Detect trade boundaries
    # entry is when today > 0 and yesterday == 0
    entries = (exposures[1:] > 0.0) & (exposures[:-1] == 0.0)
    exits = (exposures[1:] == 0.0) & (exposures[:-1] > 0.0)
    
    entry_indices = np.where(entries)[0] + 1
    exit_indices = np.where(exits)[0] + 1
    
    # Handle starting state edge case
    if exposures[0] > 0.0:
        entry_indices = np.insert(entry_indices, 0, 0)
        
    num_entries = len(entry_indices)
    num_exits = len(exit_indices)
    
    totalTrades = num_entries
    winTrades = 0
    
    for k in range(min(num_entries, num_exits)):
        e_idx = entry_indices[k]
        ex_idx = exit_indices[k]
        # In the exact loop:
        # stratReturn[i-1] compounds from day i_entry to i_exit-1
        # In stratReturn indices (which is 0-indexed corresponding to i-1):
        # The range is from e_idx - 1 to ex_idx - 2.
        # Let's verify:
        # Loop starts compounding when inTrade is true.
        # inTrade becomes true at the end of the day when exposure > 0 and prevExposure == 0.
        # That means on day e_idx, exposure > 0 and prevExposure == 0 (exposures[e_idx] > 0 and exposures[e_idx-1] == 0).
        # At day e_idx, inTrade is set to true.
        # But wait! On day e_idx, stratReturn was calculated as:
        #   stratReturn = prevExposure * btcDailyReturn = exposures[e_idx-1] * btcDailyReturn = 0 * btcDailyReturn = 0.
        # So stratReturn on day e_idx is 0.
        # Then at the end of day e_idx, inTrade is set to true.
        # So on day e_idx+1, inTrade is already true, and stratReturn = exposures[e_idx] * btcDailyReturn.
        # The compound return starts compounding on day e_idx+1.
        # It stops compounding when exposure == 0 and prevExposure > 0 (which happens on day ex_idx, where exposures[ex_idx] == 0 and exposures[ex_idx-1] > 0).
        # On day ex_idx, stratReturn is exposures[ex_idx-1] * btcDailyReturn (which is > 0).
        # The loop compounds on day ex_idx, and then sets inTrade to false (so day ex_idx+1 is not compounded).
        # Therefore, the compounded days are from e_idx+1 to ex_idx.
        # In stratReturn indices (which are i-1):
        # e_idx+1 corresponds to index e_idx.
        # ex_idx corresponds to index ex_idx-1.
        # So the slice is stratReturn[e_idx : ex_idx].
        tr = np.prod(1.0 + stratReturn[e_idx : ex_idx]) - 1.0
        if tr > 0.0:
            winTrades += 1
            
    winRate = (winTrades / totalTrades) * 100.0 if totalTrades > 0 else 0.0
    
    return {
        "strategy_return": totalReturnPct,
        "cagr": cagr,
        "max_dd": maxDrawdown * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "win_rate": winRate,
        "total_trades": totalTrades,
        "win_trades": winTrades
    }

def main():
    df = load_data()
    # Mock some random exposures
    np.random.seed(42)
    exposures = np.zeros(len(df))
    prev = 0.0
    for i in range(len(df)):
        if np.random.rand() < 0.1:
            prev = 1.0 - prev
        exposures[i] = prev
        
    m1 = calculate_metrics_exact(df, exposures)
    m2 = calculate_metrics_vectorized(df, exposures)
    
    print("Exact:")
    print(m1)
    print("Vectorized:")
    print(m2)
    
    match = True
    for k in m1:
        if abs(m1[k] - m2[k]) > 1e-7:
            print(f"Mismatch in {k}: {m1[k]} vs {m2[k]}")
            match = False
            
    if match:
        print("SUCCESS: Vectorized metrics match Exact metrics perfectly!")
    else:
        print("FAIL: Metrics mismatch.")

if __name__ == "__main__":
    main()
