import sqlite3
import pandas as pd
import numpy as np

def calculate_ichimoku_rules(df):
    # Sort by timestamp to ensure chronological order
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Calculate daily log returns and shift by -1 to get the next day's return
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    df['target'] = df['log_ret'].shift(-1)
    
    # Calculate components
    # Tenkan (T) = (Max High + Min Low)/2 over 9 periods
    high_9 = df['high'].rolling(9).max()
    low_9 = df['low'].rolling(9).min()
    df['T'] = (high_9 + low_9) / 2
    
    # Kijun (K) = (Max High + Min Low)/2 over 26 periods
    high_26 = df['high'].rolling(26).max()
    low_26 = df['low'].rolling(26).min()
    df['K'] = (high_26 + low_26) / 2
    
    # Senkou A (SA) = (T + K)/2, shifted forward 26
    df['SA'] = ((df['T'] + df['K']) / 2).shift(26)
    
    # Senkou B (SB) = (Max High + Min Low)/2 over 52 periods, shifted forward 26
    high_52 = df['high'].rolling(52).max()
    low_52 = df['low'].rolling(52).min()
    df['SB'] = ((high_52 + low_52) / 2).shift(26)
    
    # Price (P) = Current Close
    df['P'] = df['close']
    
    # Chikou Causal (C) = Current close shifted back 26 periods (price 26 days ago)
    df['C'] = df['close'].shift(26)
    
    # Drop NaNs
    df = df.dropna().copy()
    
    # Define boolean rules
    rules = {
        'P > T': df['P'] > df['T'],
        'P < T': df['P'] < df['T'],
        'P > K': df['P'] > df['K'],
        'P < K': df['P'] < df['K'],
        'P > SA': df['P'] > df['SA'],
        'P < SA': df['P'] < df['SA'],
        'P > SB': df['P'] > df['SB'],
        'P < SB': df['P'] < df['SB'],
        'P > C': df['P'] > df['C'],
        'P < C': df['P'] < df['C'],
        'T > K': df['T'] > df['K'],
        'T < K': df['T'] < df['K'],
        'SA > SB': df['SA'] > df['SB'],
        'SA < SB': df['SA'] < df['SB'],
    }
    
    rule_names = list(rules.keys())
    
    results = []
    
    # Single rules
    for r1 in rule_names:
        signal = rules[r1].astype(int)
        strat_returns = signal * df['target']
        mean_ret = strat_returns.mean()
        std_ret = strat_returns.std()
        sharpe = (mean_ret / std_ret) * np.sqrt(365) if std_ret > 0 else 0
        cagr = np.exp(strat_returns.sum() / len(df) * 365) - 1
        results.append({
            'Rule': r1,
            'Sharpe': sharpe,
            'CAGR': cagr,
            'Trades_pct': signal.mean()
        })
        
    # Combinations of 2 rules
    for i in range(len(rule_names)):
        for j in range(i+1, len(rule_names)):
            r1, r2 = rule_names[i], rule_names[j]
            # Avoid combining exact opposites (e.g., P > T and P < T)
            if r1.split(' ')[0] == r2.split(' ')[0] and r1.split(' ')[2] == r2.split(' ')[2]:
                continue
                
            signal = (rules[r1] & rules[r2]).astype(int)
            strat_returns = signal * df['target']
            mean_ret = strat_returns.mean()
            std_ret = strat_returns.std()
            sharpe = (mean_ret / std_ret) * np.sqrt(365) if std_ret > 0 else 0
            cagr = np.exp(strat_returns.sum() / len(df) * 365) - 1
            results.append({
                'Rule': f"{r1} AND {r2}",
                'Sharpe': sharpe,
                'CAGR': cagr,
                'Trades_pct': signal.mean()
            })
            
    res_df = pd.DataFrame(results).sort_values('Sharpe', ascending=False)
    print(res_df.head(10).to_string(index=False))

if __name__ == '__main__':
    conn = sqlite3.connect('database/lttd.db')
    try:
        # Check if daily_price exists, else use ohlcv
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        if 'daily_price' in tables['name'].values:
            df = pd.read_sql("SELECT * FROM daily_price", conn)
        else:
            df = pd.read_sql("SELECT * FROM ohlcv", conn)
    finally:
        conn.close()
        
    calculate_ichimoku_rules(df)
