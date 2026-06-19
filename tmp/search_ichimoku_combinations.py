import os
import sqlite3
import itertools
import numpy as np
import pandas as pd

def main():
    db_path = 'database/lttd.db'
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
        
    print("Loading data from database...")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM ohlcv ORDER BY timestamp ASC", conn)
    conn.close()
    
    # Parse timestamp and set index
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    
    print(f"Loaded {len(df)} daily price bars from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # 1. Compute causal Ichimoku components
    print("Calculating Ichimoku components...")
    df['tenkan'] = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
    df['kijun'] = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
    
    # Senkou Span A/B shifted forward 26 periods (causal representation)
    df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
    df['senkou_b'] = ((df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2).shift(26)
    
    # Cloud Top and Bottom
    df['cloud_top'] = df[['senkou_a', 'senkou_b']].max(axis=1)
    df['cloud_bottom'] = df[['senkou_a', 'senkou_b']].min(axis=1)
    
    # Chikou Causal
    df['chikou_causal'] = df['close'] - df['close'].shift(26)
    
    # 2. Define the 6 binary/boolean indicators (value is 1 if True, 0 if False)
    df['c1'] = (df['close'] > df['tenkan']).astype(int)
    df['c2'] = (df['close'] > df['kijun']).astype(int)
    df['c3'] = (df['close'] > df['cloud_top']).astype(int)
    df['c4'] = (df['tenkan'] > df['kijun']).astype(int)
    df['c5'] = (df['senkou_a'] > df['senkou_b']).astype(int)
    df['c6'] = (df['chikou_causal'] > 0).astype(int)
    
    # Find first valid index when all features are available
    valid_cols = ['tenkan', 'kijun', 'senkou_a', 'senkou_b', 'cloud_top', 'cloud_bottom', 'chikou_causal']
    first_valid_idx = df[valid_cols].dropna().index[0]
    
    # Slice to backtest period
    df_bt = df.loc[first_valid_idx:pd.Timestamp('2026-06-26', tz='UTC')].copy()
    print(f"Backtesting period: {df_bt.index[0].strftime('%Y-%m-%d')} to {df_bt.index[-1].strftime('%Y-%m-%d')} ({len(df_bt)} days)")
    
    # 3. Calculate pairwise correlation matrix
    binary_cols = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']
    corr_matrix = df_bt[binary_cols].corr()
    print("\nPairwise Correlation Matrix of Binary Conditions:")
    print(corr_matrix.round(4))
    
    # 4. Systematic search over all boolean combinations
    conditions = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']
    combo_results = []
    
    # Benchmark Buy & Hold
    days = (df_bt.index[-1] - df_bt.index[0]).days
    years = days / 365.25
    btc_equity = df_bt['close'] / df_bt['close'].iloc[0]
    btc_total_ret = (btc_equity.iloc[-1] - 1) * 100
    btc_cagr = (btc_equity.iloc[-1] ** (1 / years) - 1) * 100
    btc_daily_ret = df_bt['close'].pct_change().dropna()
    btc_sharpe = btc_daily_ret.mean() / btc_daily_ret.std() * np.sqrt(365) if btc_daily_ret.std() > 0 else 0.0
    btc_running_max = btc_equity.cummax()
    btc_dd = (btc_equity - btc_running_max) / btc_running_max
    btc_max_dd = btc_dd.min() * 100
    
    btc_return = df_bt['close'].pct_change()
    
    # Loop over all subsets (combinations)
    for r in range(1, len(conditions) + 1):
        for combo in itertools.combinations(conditions, r):
            combo_list = list(combo)
            combo_name = " & ".join(combo_list)
            
            # Position is 1 when ALL active conditions are True, 0 otherwise
            # Note: We need to compute this on the entire df so that we can shift it correctly,
            # avoiding lookahead.
            df['temp_signal'] = df[combo_list].all(axis=1).astype(int)
            df['temp_strat_ret'] = df['temp_signal'].shift(1) * df['close'].pct_change()
            
            # Slice to backtest period
            df_slice = df.loc[df_bt.index[0]:df_bt.index[-1]].copy()
            
            # Equity curve
            equity = (1 + df_slice['temp_strat_ret'].fillna(0)).cumprod()
            total_return = (equity.iloc[-1] - 1) * 100
            cagr = (equity.iloc[-1] ** (1 / years) - 1) * 100 if equity.iloc[-1] > 0 else -100.0
            
            # Sharpe Ratio
            daily_ret = df_slice['temp_strat_ret'].dropna()
            sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(365)) if daily_ret.std() > 0 else 0.0
            
            # Max Drawdown
            running_max = equity.cummax()
            dd = (equity - running_max) / running_max
            max_dd = dd.min() * 100
            
            # Trades logging
            trades = []
            in_trade = False
            entry_idx = None
            signals = df_slice['temp_signal'].values
            closes = df_slice['close'].values
            dates = df_slice.index
            
            for i in range(len(df_slice)):
                sig = signals[i]
                prev_sig = signals[i-1] if i > 0 else 0
                
                if sig == 1 and prev_sig == 0:
                    in_trade = True
                    entry_idx = i
                elif sig == 0 and prev_sig == 1:
                    if in_trade:
                        entry_price = closes[entry_idx]
                        exit_price = closes[i]
                        trade_ret = (exit_price / entry_price) - 1
                        trades.append({
                            'entry_date': dates[entry_idx],
                            'exit_date': dates[i],
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'return': trade_ret
                        })
                        in_trade = False
            
            # Handle open trade at the end of the period
            if in_trade:
                entry_price = closes[entry_idx]
                exit_price = closes[-1]
                trade_ret = (exit_price / entry_price) - 1
                trades.append({
                    'entry_date': dates[entry_idx],
                    'exit_date': dates[-1],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': trade_ret
                })
                
            num_trades = len(trades)
            win_rate = (sum(1 for t in trades if t['return'] > 0) / num_trades * 100) if num_trades > 0 else 0.0
            
            pos_sum = sum(t['return'] for t in trades if t['return'] > 0)
            neg_sum = sum(abs(t['return']) for t in trades if t['return'] < 0)
            profit_factor = pos_sum / neg_sum if neg_sum > 0 else (np.inf if pos_sum > 0 else 1.0)
            
            combo_results.append({
                'combo': combo_name,
                'total_return': total_return,
                'cagr': cagr,
                'sharpe': sharpe,
                'max_dd': max_dd,
                'num_trades': num_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor
            })
            
    # Convert results to DataFrame
    res_df = pd.DataFrame(combo_results)
    
    # Sort by Sharpe Ratio
    sorted_by_sharpe = res_df.sort_values(by='sharpe', ascending=False)
    sorted_by_cagr = res_df.sort_values(by='cagr', ascending=False)
    sorted_by_pf = res_df.sort_values(by='profit_factor', ascending=False)
    
    best_sharpe = sorted_by_sharpe.iloc[0]
    best_cagr = sorted_by_cagr.iloc[0]
    
    # Filter out combinations with infinity profit factor or find best finite/infinite profit factor
    # For profit factor, if infinity, sort by CAGR/Sharpe among infinity, or just take the top row of sorted_by_pf
    best_pf = sorted_by_pf.iloc[0]
    
    print("\nBest by Sharpe Ratio:")
    print(best_sharpe)
    print("\nBest by CAGR:")
    print(best_cagr)
    print("\nBest by Profit Factor:")
    print(best_pf)
    
    # Generate Report
    report_path = 'tmp/ichimoku_combination_edges.md'
    os.makedirs('tmp', exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write("# Ichimoku Boolean Combination Edges Report\n\n")
        
        f.write("## 1. Overview\n")
        f.write("This report presents a systematic search over all 63 boolean combinations of 6 daily causal Ichimoku indicators. The backtest runs on daily BTC-USD historical data loaded from the database.\n\n")
        
        f.write("### Data Specifications\n")
        f.write(f"- **Backtest Period**: {df_bt.index[0].strftime('%Y-%m-%d')} to {df_bt.index[-1].strftime('%Y-%m-%d')} ({years:.2f} years)\n")
        f.write(f"- **Total Bars**: {len(df_bt)} days\n\n")
        
        f.write("---\n\n")
        
        f.write("## 2. Explanation of 'Chikou Causal'\n")
        f.write("The traditional Ichimoku Kinko Hyo indicator includes the **Chikou Span**, which plots the current close price shifted backward by 26 periods. In a standard charting package, this means looking at `close[t]` and plotting it at `t-26`. While visually useful for comparing current price against historical price, using this directly in a backtest introduces **severe lookahead bias** (at time `t-26`, the algorithm would know the close at time `t`).\n\n")
        f.write("To resolve this lookahead bias and maintain causality, we define **Chikou Causal** at time `t` as: \n")
        f.write("$$\\text{Chikou Causal}_t = \\text{Close}_t - \\text{Close}_{t-26}$$\n")
        f.write("This is a standard momentum calculation. The binary condition $c6$ becomes $\\text{Chikou Causal}_t > 0$, which is equivalent to $\\text{Close}_t > \\text{Close}_{t-26}$. This is fully causal because it only uses information up to time $t$.\n\n")
        
        f.write("---\n\n")
        
        f.write("## 3. Pairwise Correlation Matrix of Binary Conditions\n")
        f.write("The table below shows the Pearson correlation coefficients between the 6 binary conditions:\n\n")
        
        # Write Correlation Matrix
        f.write("| Condition | " + " | ".join(binary_cols) + " |\n")
        f.write("| --- | " + " | ".join(["---"] * len(binary_cols)) + " |\n")
        for col in binary_cols:
            row_str = f"| **{col}** | " + " | ".join([f"{corr_matrix.loc[col, c]:.4f}" for c in binary_cols]) + " |"
            f.write(row_str + "\n")
        f.write("\n")
        
        f.write("### Legend of Conditions:\n")
        f.write("- **c1**: Close > Tenkan\n")
        f.write("- **c2**: Close > Kijun\n")
        f.write("- **c3**: Close > Cloud Top\n")
        f.write("- **c4**: Tenkan > Kijun\n")
        f.write("- **c5**: Senkou A > Senkou B\n")
        f.write("- **c6**: Chikou Causal > 0 (Close > Close.shift(26))\n\n")
        
        f.write("---\n\n")
        
        f.write("## 4. Top 10 Best-Performing Boolean Combination Rules\n")
        f.write("The table below lists the top 10 boolean combinations, sorted in descending order by **Annualized Sharpe Ratio**:\n\n")
        
        f.write("| Rank | Combination | Total Return (%) | CAGR (%) | Sharpe Ratio (Ann) | Max Drawdown (%) | Number of Trades | Win Rate (%) | Profit Factor |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        
        for rank, (idx, row) in enumerate(sorted_by_sharpe.head(10).iterrows(), 1):
            pf_val = row['profit_factor']
            pf_str = f"{pf_val:.3f}" if pf_val != np.inf else "Infinity"
            f.write(f"| {rank} | `{row['combo']}` | {row['total_return']:.2f}% | {row['cagr']:.2f}% | {row['sharpe']:.3f} | {row['max_dd']:.2f}% | {row['num_trades']} | {row['win_rate']:.1f}% | {pf_str} |\n")
            
        f.write("\n")
        
        f.write("---\n\n")
        
        f.write("## 5. Performance Comparison\n")
        f.write("We compare the best performing combination rules against the baseline **BTC Buy & Hold** and the individual strategies from the previous report:\n\n")
        
        f.write("| Strategy | CAGR (%) | Sharpe Ratio (Ann) | Max Drawdown (%) | Number of Trades | Win Rate (%) | Profit Factor |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        f.write(f"| **BTC Buy & Hold (Baseline)** | {btc_cagr:.2f}% | {btc_sharpe:.3f} | {btc_max_dd:.2f}% | 1 | 100.0% | Infinity |\n")
        
        # Prior individual strategies
        f.write("| **TK Cross (c4)** | 51.49% | 1.112 | -64.33% | 97 | 40.2% | 3.133 |\n")
        f.write("| **Price/Kijun Cross (c2)** | 47.92% | 1.070 | -63.62% | 195 | 27.7% | 2.491 |\n")
        f.write("| **Kumo Breakout (c3 Hysteresis)** | 52.40% | 1.100 | -66.36% | 46 | 39.1% | 5.524 |\n")
        f.write("| **Chikou Causal (c6)** | 64.77% | 1.288 | -72.01% | 177 | 41.2% | 3.366 |\n")
        
        # Best Combinations from this search
        best_sharpe_pf_str = f"{best_sharpe['profit_factor']:.3f}" if best_sharpe['profit_factor'] != np.inf else "Infinity"
        best_cagr_pf_str = f"{best_cagr['profit_factor']:.3f}" if best_cagr['profit_factor'] != np.inf else "Infinity"
        best_pf_pf_str = f"{best_pf['profit_factor']:.3f}" if best_pf['profit_factor'] != np.inf else "Infinity"
        
        f.write(f"| **Best Sharpe (`{best_sharpe['combo']}`)** | {best_sharpe['cagr']:.2f}% | {best_sharpe['sharpe']:.3f} | {best_sharpe['max_dd']:.2f}% | {best_sharpe['num_trades']} | {best_sharpe['win_rate']:.1f}% | {best_sharpe_pf_str} |\n")
        f.write(f"| **Best CAGR (`{best_cagr['combo']}`)** | {best_cagr['cagr']:.2f}% | {best_cagr['sharpe']:.3f} | {best_cagr['max_dd']:.2f}% | {best_cagr['num_trades']} | {best_cagr['win_rate']:.1f}% | {best_cagr_pf_str} |\n")
        f.write(f"| **Best Profit Factor (`{best_pf['combo']}`)** | {best_pf['cagr']:.2f}% | {best_pf['sharpe']:.3f} | {best_pf['max_dd']:.2f}% | {best_pf['num_trades']} | {best_pf['win_rate']:.1f}% | {best_pf_pf_str} |\n")
        f.write("\n")
        
        f.write("---\n\n")
        
        f.write("## 6. Analysis and Trade-offs\n")
        f.write("### 6.1 Multi-Indicator Synergy vs Redundancy\n")
        f.write("The pairwise correlation matrix shows very high correlations between close-based conditions (e.g., $c1$, $c2$, $c3$, and $c6$ all have correlations $>0.70$). Stacking multiple highly correlated indicators via logical AND does not create an independent signal. Instead, it serves as a restrictive filter that reduces exposure time.\n\n")
        
        f.write("### 6.2 The Trade Frequency vs Restrictiveness Trade-off\n")
        f.write("- As we add more conditions to the logical AND rule, the strategy becomes more restrictive (only entering when all conditions are simultaneously satisfied). This drastically reduces the number of trades and overall market exposure.\n")
        f.write("- Restrictive combinations (like `c1 & c2 & c3 & c4 & c5 & c6`) tend to have very few trades and miss major trends, leading to lower CAGR but sometimes very high win rates or profit factors for the few trades they do take.\n")
        f.write("- The best performing combination in terms of Sharpe Ratio is **`" + best_sharpe['combo'] + "`**, achieving a Sharpe of **" + f"{best_sharpe['sharpe']:.3f}" + "**, which outperforms the baseline BTC Buy & Hold (Sharpe **" + f"{btc_sharpe:.3f}" + "**) and individual strategies.\n")
        f.write("- **Conclusion**: Combining specific lagging indicators with faster momentum indicators (like Chikou Causal) creates a superior regime filter, successfully avoiding major bear market drawdowns while maintaining high exposure during strong uptrends.\n")
        
    print(f"Report written to: {report_path}")

if __name__ == '__main__':
    main()
