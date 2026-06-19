import sqlite3
import pandas as pd
import numpy as np
import os

def main():
    print("Loading historical BTC data...")
    # Connect to the SQLite database
    db_path = 'database/lttd.db'
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
        
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
    
    # 2. Implement and simulate strategies (1 = bullish, 0 = bearish/cash)
    df['tk_signal'] = (df['tenkan'] > df['kijun']).astype(int)
    df['pk_signal'] = (df['close'] > df['kijun']).astype(int)
    
    # Kumo Breakout with Hysteresis
    kumo_signal = []
    state = 0
    for i in range(len(df)):
        c = df['close'].iloc[i]
        top = df['cloud_top'].iloc[i]
        bot = df['cloud_bottom'].iloc[i]
        
        if pd.isna(top) or pd.isna(bot):
            state = 0
        else:
            if c > top:
                state = 1
            elif c < bot:
                state = 0
            # If inside the cloud (bot <= c <= top), keep previous state
        kumo_signal.append(state)
    df['kumo_signal'] = kumo_signal
    
    df['chikou_signal'] = (df['close'] > df['close'].shift(26)).astype(int)
    
    # 3. Calculate forward returns for edge analysis
    df['forward_7d'] = df['close'].shift(-7) / df['close'] - 1
    df['forward_14d'] = df['close'].shift(-14) / df['close'] - 1
    df['forward_30d'] = df['close'].shift(-30) / df['close'] - 1
    
    # Baseline forward returns over the ENTIRE history
    baseline_7d = df['forward_7d'].mean() * 100
    baseline_14d = df['forward_14d'].mean() * 100
    baseline_30d = df['forward_30d'].mean() * 100
    
    # Find first valid index where all Ichimoku components are calculated
    valid_cols = ['tenkan', 'kijun', 'senkou_a', 'senkou_b', 'cloud_top', 'cloud_bottom']
    first_valid_idx = df[valid_cols].dropna().index[0]
    
    print(f"Backtesting period: {first_valid_idx.strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    df_bt = df.loc[first_valid_idx:].copy()
    
    # Calculate baseline forward returns over the backtest period
    baseline_7d_bt = df_bt['forward_7d'].mean() * 100
    baseline_14d_bt = df_bt['forward_14d'].mean() * 100
    baseline_30d_bt = df_bt['forward_30d'].mean() * 100
    
    strategies = [
        ('TK Cross', 'tk_signal'),
        ('Price/Kijun Cross', 'pk_signal'),
        ('Kumo Breakout', 'kumo_signal'),
        ('Chikou Causal', 'chikou_signal')
    ]
    
    results = []
    
    for name, signal_col in strategies:
        # Calculate daily strategy returns (causal: trade at t-1 close, get return at t)
        df['btc_return'] = df['close'].pct_change()
        df['strat_ret'] = df[signal_col].shift(1) * df['btc_return']
        
        # Sliced df for backtest metrics
        df_slice = df.loc[first_valid_idx:].copy()
        
        # Cumulative Equity
        equity = (1 + df_slice['strat_ret'].fillna(0)).cumprod()
        total_return = (equity.iloc[-1] - 1) * 100
        
        # CAGR
        days = (df_slice.index[-1] - df_slice.index[0]).days
        years = days / 365.25
        cagr = (equity.iloc[-1] ** (1 / years) - 1) * 100 if equity.iloc[-1] > 0 else -100.0
        
        # Sharpe Ratio
        daily_ret = df_slice['strat_ret'].dropna()
        sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(365)) if daily_ret.std() > 0 else 0.0
        
        # Max Drawdown
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max
        max_dd = dd.min() * 100
        
        # Trades
        trades = []
        in_trade = False
        entry_idx = None
        signals = df_slice[signal_col].values
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
        
        # Crossover triggers for forward return edge
        trigger_cond = (df[signal_col] == 1) & (df[signal_col].shift(1) == 0)
        # Slices triggers to within the backtest period
        trigger_dates = df.index[trigger_cond & (df.index >= first_valid_idx) & (df.index <= df.index[-1])]
        
        fwd_7d = df.loc[trigger_dates, 'forward_7d'].mean() * 100
        fwd_14d = df.loc[trigger_dates, 'forward_14d'].mean() * 100
        fwd_30d = df.loc[trigger_dates, 'forward_30d'].mean() * 100
        
        results.append({
            'name': name,
            'total_return': total_return,
            'cagr': cagr,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'fwd_7d': fwd_7d,
            'fwd_14d': fwd_14d,
            'fwd_30d': fwd_30d,
            'num_triggers': len(trigger_dates)
        })
        
        # Benchmark buy & hold for comparison
        if name == 'TK Cross': # Only compute once
            btc_equity = df_slice['close'] / df_slice['close'].iloc[0]
            btc_total_ret = (btc_equity.iloc[-1] - 1) * 100
            btc_cagr = (btc_equity.iloc[-1] ** (1 / years) - 1) * 100
            btc_daily_ret = df_slice['close'].pct_change().dropna()
            btc_sharpe = btc_daily_ret.mean() / btc_daily_ret.std() * np.sqrt(365)
            btc_running_max = btc_equity.cummax()
            btc_dd = (btc_equity - btc_running_max) / btc_running_max
            btc_max_dd = btc_dd.min() * 100
            
            benchmark_stats = {
                'name': 'BTC Buy & Hold',
                'total_return': btc_total_ret,
                'cagr': btc_cagr,
                'sharpe': btc_sharpe,
                'max_dd': btc_max_dd,
                'num_trades': 1,
                'win_rate': 100.0,
                'profit_factor': np.inf,
                'fwd_7d': np.nan,
                'fwd_14d': np.nan,
                'fwd_30d': np.nan,
                'num_triggers': np.nan
            }

    # Generate Markdown report
    print("Generating report...")
    report_path = 'tmp/ichimoku_statistical_edges.md'
    
    with open(report_path, 'w') as f:
        f.write("# Ichimoku Kinko Hyo Statistical Edges and Backtest Report\n\n")
        f.write("## Overview\n")
        f.write("This report presents a rigorous backtesting and statistical edge analysis of four daily long-only trading strategies derived from the **Ichimoku Kinko Hyo** indicator. The backtest runs on daily BTC-USD historical data loaded from the database.\n\n")
        
        f.write("### Data Specifications\n")
        f.write(f"- **Total Bars**: {len(df)} days\n")
        f.write(f"- **Backtest Period**: {first_valid_idx.strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({years:.2f} years)\n")
        f.write(f"- **Baseline Period**: Full database history ({len(df)} days)\n\n")
        
        f.write("## Strategy Performance Metrics\n\n")
        f.write("| Strategy | Total Return (%) | CAGR (%) | Sharpe Ratio (Ann) | Max Drawdown (%) | Number of Trades | Win Rate (%) | Profit Factor |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        
        # Write benchmark first
        f.write(f"| **{benchmark_stats['name']}** | {benchmark_stats['total_return']:.2f}% | {benchmark_stats['cagr']:.2f}% | {benchmark_stats['sharpe']:.3f} | {benchmark_stats['max_dd']:.2f}% | {benchmark_stats['num_trades']} | {benchmark_stats['win_rate']:.1f}% | {benchmark_stats['profit_factor']} |\n")
        
        for res in results:
            pf_str = f"{res['profit_factor']:.3f}" if res['profit_factor'] != np.inf else "Infinity"
            f.write(f"| {res['name']} | {res['total_return']:.2f}% | {res['cagr']:.2f}% | {res['sharpe']:.3f} | {res['max_dd']:.2f}% | {res['num_trades']} | {res['win_rate']:.1f}% | {pf_str} |\n")
            
        f.write("\n> [!NOTE]\n")
        f.write("> All metrics are calculated daily. The Sharpe Ratio is annualized using a 365-day year and a 0% risk-free rate. Performance is net of zero fees (execution only).\n\n")
        
        f.write("## Out-of-Sample Forward Edge Analysis\n")
        f.write("We evaluate the predictive edge of each bullish crossover trigger by calculating the average forward returns of BTC-USD over 7-day, 14-day, and 30-day horizons. We compare these results against both the **Full History Baseline** and the **Backtest Period Baseline** to confirm if a true statistical edge exists.\n\n")
        
        f.write("| Strategy / Baseline | Triggers | Avg 7-Day Fwd Return | 7d Edge vs Full (B.T.) | Avg 14-Day Fwd Return | 14d Edge vs Full (B.T.) | Avg 30-Day Fwd Return | 30d Edge vs Full (B.T.) |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        
        # Write baselines
        f.write(f"| **Full History Baseline** | - | {baseline_7d:.2f}% | - | {baseline_14d:.2f}% | - | {baseline_30d:.2f}% | - |\n")
        f.write(f"| **Backtest Period Baseline** | - | {baseline_7d_bt:.2f}% | - | {baseline_14d_bt:.2f}% | - | {baseline_30d_bt:.2f}% | - |\n")
        
        for res in results:
            edge_7d_full = res['fwd_7d'] - baseline_7d
            edge_7d_bt = res['fwd_7d'] - baseline_7d_bt
            edge_14d_full = res['fwd_14d'] - baseline_14d
            edge_14d_bt = res['fwd_14d'] - baseline_14d_bt
            edge_30d_full = res['fwd_30d'] - baseline_30d
            edge_30d_bt = res['fwd_30d'] - baseline_30d_bt
            
            f.write(f"| {res['name']} | {res['num_triggers']} | {res['fwd_7d']:.2f}% | **{edge_7d_full:+.2f}%** ({edge_7d_bt:+.2f}%) | {res['fwd_14d']:.2f}% | **{edge_14d_full:+.2f}%** ({edge_14d_bt:+.2f}%) | {res['fwd_30d']:.2f}% | **{edge_30d_full:+.2f}%** ({edge_30d_bt:+.2f}%) |\n")
            
        f.write("\n> [!TIP]\n")
        f.write("> A positive edge (bolded above vs Full History) indicates that buying the bullish crossover of the strategy yields outperformance relative to the unconditional baseline return over that horizon.\n\n")
        
        f.write("## Key Findings\n")
        f.write("1. **Trend Following Efficiency**: Compare the CAGR and Sharpe ratios of the strategies against BTC Buy & Hold. Identify which strategy offers the best risk-adjusted return (highest Sharpe Ratio and lowest Max Drawdown).\n")
        f.write("2. **Hysteresis in Kumo Breakout**: Observe how the Kumo Breakout strategy performs. The cloud acts as a noise-filter, reducing the number of trades and whipsaws compared to faster crosses (like TK Cross).\n")
        f.write("3. **Statistical Edge**: Verify which crossover triggers show the strongest forward return outperformance over the 7, 14, and 30-day horizons. A rising edge over longer horizons indicates strong post-trigger momentum continuation.\n")
        
    print(f"Report successfully saved to: {os.path.abspath(report_path)}")

if __name__ == '__main__':
    main()
