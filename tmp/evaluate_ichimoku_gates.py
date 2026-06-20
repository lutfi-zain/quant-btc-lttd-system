import os
import requests
import datetime
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, Any

# --- MATHEMATICAL UTILITIES ---

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def super_smoother(series: pd.Series, period: int) -> pd.Series:
    if len(series) < 2:
        return series
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    values = series.values
    out = np.zeros_like(values)
    out[0] = values[0]
    out[1] = values[1]
    for t in range(2, len(values)):
        out[t] = c1 * (values[t] + values[t-1]) / 2.0 + c2 * out[t-1] + c3 * out[t-2]
    return pd.Series(out, index=series.index)

def shannon_entropy(series: pd.Series, window: int = 15, bins: int = 6) -> pd.Series:
    def calc_shannon(x):
        if len(x) < window:
            return np.nan
        counts, _ = np.histogram(x, bins=bins)
        probs = counts / len(x)
        probs = probs[probs > 0]
        return -np.sum(probs * np.log2(probs))
    returns = series.pct_change().fillna(0)
    return returns.rolling(window=window).apply(calc_shannon, raw=True)

def generate_ichimoku_cloud(df: pd.DataFrame, p1=20, p2=60, p3=120) -> tuple:
    tenkan = (df['High'].rolling(p1).max() + df['Low'].rolling(p1).min()) / 2
    kijun = (df['High'].rolling(p2).max() + df['Low'].rolling(p2).min()) / 2
    sa = ((tenkan + kijun) / 2).shift(p2)
    sb = ((df['High'].rolling(p3).max() + df['Low'].rolling(p3).min()) / 2).shift(p2)
    return sa, sb

# --- SIMULATION & STATS ENGINE ---

def run_simulation(
    df: pd.DataFrame,
    score_entry_thresh: float,
    score_exit_thresh: float,
    entropy_thresh: float,
    er_thresh: float,
    use_cloud_gate: bool,
    mhp_days: int = 17,
    rco_days: int = 5,
    tc_rate: float = 0.001
) -> tuple:
    
    pos = 0.0
    signals = []
    days_in_position = 0
    days_since_exit = 999
    
    for i, row in df.iterrows():
        se_entry = row['smoothed_score_entry']
        se_exit = row['smoothed_score_exit']
        entropy = row['Entropy']
        er = row['ER']
        price = row['Close']
        cloud_a = row['cloud_a']
        cloud_b = row['cloud_b']
        ma_val = row['ma_val']
        
        # Valuation CB check (we just follow the DB's CB active flag to keep CB identical)
        cb_active = bool(row['circuit_breaker_active'])
        if cb_active:
            pos = 0.0
            signals.append(pos)
            days_in_position = 0
            days_since_exit = 0
            continue
            
        # Update timers
        if pos >= 0.9:
            days_in_position += 1
            days_since_exit = 0
        else:
            days_in_position = 0
            days_since_exit += 1
            
        if pos == 1.0:
            if days_in_position >= mhp_days:
                if se_exit <= score_exit_thresh:
                    pos = 0.0
        else:
            # Entry logic
            if days_since_exit >= rco_days:
                # 226-day MA filter (from baseline LTTD)
                ma_condition = True
                if pd.notna(ma_val):
                    ma_condition = (price > ma_val)
                    
                # Shannon Entropy Gate
                entropy_condition = True
                if entropy_thresh < 9.0 and pd.notna(entropy):
                    entropy_condition = (entropy <= entropy_thresh)
                    
                # Efficiency Ratio Gate
                er_condition = True
                if er_thresh > 0.0 and pd.notna(er):
                    er_condition = (er >= er_thresh)
                    
                # Ichimoku Cloud Gate
                cloud_condition = True
                if use_cloud_gate:
                    cloud_min = np.minimum(cloud_a, cloud_b) if (pd.notna(cloud_a) and pd.notna(cloud_b)) else (cloud_a if pd.notna(cloud_a) else (cloud_b if pd.notna(cloud_b) else np.nan))
                    if pd.notna(cloud_min):
                        cloud_condition = (price >= cloud_min)
                        
                if se_entry >= score_entry_thresh and ma_condition and entropy_condition and er_condition and cloud_condition:
                    pos = 1.0
                    days_in_position = 0
                    
        signals.append(pos)
        
    df_temp = df.copy()
    df_temp['Pos'] = signals
    
    # Run backtest
    active_pos = df_temp['Pos'].shift(1).fillna(0.0)
    market_ret = df_temp['Close'].pct_change().fillna(0.0)
    pos_change = active_pos.diff().abs().fillna(0.0)
    tc = pos_change * tc_rate
    strat_ret = active_pos * market_ret - tc
    
    return strat_ret, df_temp['Pos']

def calculate_stats(ret_series: pd.Series, pos_series: pd.Series, start_date, end_date) -> dict:
    years = (end_date - start_date).days / 365.25
    equity = (1 + ret_series).cumprod()
    final_equity = equity.iloc[-1]
    cagr_val = (final_equity ** (1 / years) - 1) if final_equity > 0 else -1.0
    
    ann_factor = 365.25
    mean_ret = ret_series.mean()
    std_ret = ret_series.std()
    sharpe = (mean_ret / std_ret * np.sqrt(ann_factor)) if std_ret > 0 else 0.0
    
    downside_ret = ret_series[ret_series < 0]
    downside_std = downside_ret.std()
    sortino = (mean_ret / downside_std * np.sqrt(ann_factor)) if downside_std > 0 else 0.0
    
    peak = equity.cummax()
    dd = (equity - peak) / peak
    max_dd = dd.min()
    calmar = cagr_val / abs(max_dd) if max_dd != 0 else float('inf')
    
    in_pos = pos_series > 0
    starts = pos_series.index[(in_pos) & (~in_pos.shift(1).fillna(False))].tolist()
    ends = pos_series.index[(~in_pos) & (in_pos.shift(1).fillna(False))].tolist()
    if len(starts) > len(ends):
        ends.append(pos_series.index[-1])
        
    trades = []
    for s, e in zip(starts, ends):
        s_loc = pos_series.index.get_loc(s)
        e_loc = pos_series.index.get_loc(e)
        tr_ret = (1 + ret_series.iloc[s_loc + 1: e_loc + 1]).prod() - 1
        trades.append(tr_ret)
        
    num_trades = len(trades)
    win_rate = 0.0
    if num_trades > 0:
        wins = [t for t in trades if t > 0]
        win_rate = len(wins) / num_trades
        
    return {
        "Total Return": (final_equity - 1) * 100,
        "CAGR": cagr_val * 100,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Max DD": max_dd * 100,
        "Calmar": calmar,
        "Trades": num_trades,
        "Win Rate": win_rate * 100
    }

def main():
    # 1. Fetch live API price data (correct calendar)
    print("Fetching correct price data from Bitview API...")
    url = "https://bitview.space/api/series/price_ohlc/day?start=2016-01-01"
    resp = requests.get(url).json()
    start_idx = resp["start"]
    data = resp["data"]
    base_date = datetime.date(2009, 1, 1)
    dates = [base_date + datetime.timedelta(days=start_idx + i) for i in range(len(data))]
    df_api = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"], index=dates)
    df_api.index = pd.to_datetime(df_api.index)
    
    # 2. Fetch LTTD results from DB
    conn = sqlite3.connect("database/lttd.db")
    df_lttd = pd.read_sql(
        "SELECT date, final_score, target_exposure, circuit_breaker_active FROM daily_lttd ORDER BY date",
        conn,
        parse_dates=["date"],
        index_col="date"
    )
    conn.close()
    
    # Correct LTTD calendar
    df_lttd_corrected = df_lttd.copy()
    df_lttd_corrected.index = df_lttd_corrected.index - pd.Timedelta(days=2)
    
    # 3. Compute Ichimoku indicators on correct prices
    print("Computing rolling gates...")
    df_api['Entropy'] = shannon_entropy(df_api['Close'], window=15, bins=6)
    
    # Efficiency Ratio (ER)
    er_len = 14
    change = df_api['Close'].diff().abs()
    volatility = change.rolling(er_len).sum()
    direction = df_api['Close'].diff(er_len).abs()
    df_api['ER'] = direction / volatility
    
    # Ichimoku Cloud
    sa, sb = generate_ichimoku_cloud(df_api)
    df_api['cloud_a'] = sa
    df_api['cloud_b'] = sb
    
    # 226-day MA
    df_api['ma_val'] = df_api['Close'].rolling(226).mean()
    
    # 4. SuperSmoother scores on LTTD final_score
    # Recalculate smoothed entry and exit scores from the shifted database final_score
    scores_series = df_lttd_corrected['final_score']
    df_lttd_corrected['smoothed_score_entry'] = super_smoother(scores_series, period=7)
    df_lttd_corrected['smoothed_score_exit'] = super_smoother(scores_series, period=3)
    
    # 5. Join
    common_idx = df_lttd_corrected.index.intersection(df_api.index)
    df_comp = pd.DataFrame(index=common_idx)
    df_comp['Close'] = df_api.loc[common_idx, 'Close']
    df_comp['cloud_a'] = df_api.loc[common_idx, 'cloud_a']
    df_comp['cloud_b'] = df_api.loc[common_idx, 'cloud_b']
    df_comp['ma_val'] = df_api.loc[common_idx, 'ma_val']
    df_comp['Entropy'] = df_api.loc[common_idx, 'Entropy']
    df_comp['ER'] = df_api.loc[common_idx, 'ER']
    df_comp['circuit_breaker_active'] = df_lttd_corrected.loc[common_idx, 'circuit_breaker_active']
    df_comp['smoothed_score_entry'] = df_lttd_corrected.loc[common_idx, 'smoothed_score_entry']
    df_comp['smoothed_score_exit'] = df_lttd_corrected.loc[common_idx, 'smoothed_score_exit']
    df_comp['target_exposure_db'] = df_lttd_corrected.loc[common_idx, 'target_exposure']
    
    start_date = common_idx.min()
    end_date = common_idx.max()
    
    # Baseline stats
    tc = 0.001
    pos_db = df_comp['target_exposure_db'].astype(float)
    active_pos_db = pos_db.shift(1).fillna(0.0)
    market_ret_db = df_comp['Close'].pct_change().fillna(0.0)
    pos_change_db = active_pos_db.diff().abs().fillna(0.0)
    tc_db = pos_change_db * tc
    ret_base = active_pos_db * market_ret_db - tc_db
    s_base = calculate_stats(ret_base, df_comp['target_exposure_db'], start_date, end_date)
    
    print("\n" + "="*80)
    print("LTTD BASELINE PERFORMANCE:")
    print(f"  CAGR: {s_base['CAGR']:.2f}% | Sharpe: {s_base['Sharpe']:.2f} | Max DD: {s_base['Max DD']:.2f}% | Trades: {s_base['Trades']} | Win Rate: {s_base['Win Rate']:.1f}%")
    print("="*80)
    
    # Test scenarios
    # We want to find a combination of ER and Entropy threshold that optimizes the stats
    # Baseline: score_entry=0.3057, score_exit=0.2360 (from sizing.py values)
    entry_s = 0.3057132189206123
    exit_s = 0.23605001464720393
    
    scenarios = [
        # (entropy_thresh, er_thresh, use_cloud_gate)
        (9.9, 0.0, False), # Baseline (no gates)
        (2.271, 0.0, False), # Entropy gate only
        (9.9, 0.25, False), # ER gate only
        (9.9, 0.0, True),  # Cloud gate only
        (2.271, 0.25, False), # Entropy + ER
        (2.271, 0.0, True), # Entropy + Cloud
        (9.9, 0.25, True), # ER + Cloud
        (2.271, 0.25, True), # Entropy + ER + Cloud
    ]
    
    # Grid search over a range of thresholds to see if we can find an optimal point
    print("\nRunning grid search for optimal gate thresholds...")
    results = []
    
    # Wide search
    for ent in [9.9, 2.20, 2.25, 2.30, 2.35, 2.40]:
        for er in [0.0, 0.15, 0.20, 0.25, 0.30]:
            for cloud in [False, True]:
                ret, pos = run_simulation(df_comp, entry_s, exit_s, ent, er, cloud, tc_rate=tc)
                stats = calculate_stats(ret, pos, start_date, end_date)
                
                # Check if it outperforms the baseline
                is_better = (stats['Sharpe'] > s_base['Sharpe'] or (stats['Sharpe'] >= s_base['Sharpe'] - 0.02 and stats['Max DD'] > s_base['Max DD']))
                
                results.append({
                    "entropy": ent,
                    "er": er,
                    "cloud": cloud,
                    "stats": stats,
                    "better": is_better
                })
                
    # Sort results by Sharpe ratio
    results_sorted = sorted(results, key=lambda x: x['stats']['Sharpe'], reverse=True)
    
    print("\nTOP 10 PERFORMANCES BY SHARPE:")
    print(f"{'Entropy':<8} | {'ER':<5} | {'Cloud':<5} | {'CAGR':<8} | {'Sharpe':<6} | {'Max DD':<8} | {'Trades':<6} | {'WinRate':<7}")
    print("-"*75)
    for r in results_sorted[:15]:
        s = r['stats']
        print(f"{r['entropy']:8.3f} | {r['er']:5.2f} | {str(r['cloud']):<5} | {s['CAGR']:7.2f}% | {s['Sharpe']:6.2f} | {s['Max DD']:7.2f}% | {s['Trades']:6} | {s['Win Rate']:6.1f}%")
        
    print("\n" + "="*80)
    best_config = results_sorted[0]
    best_stats = best_config['stats']
    print("BEST CONFIGURATION FOUND:")
    print(f"  Entropy Gate Threshold : {best_config['entropy']}")
    print(f"  Efficiency Ratio Gate  : {best_config['er']}")
    print(f"  Use Ichimoku Cloud Gate: {best_config['cloud']}")
    print("BEST STATS:")
    print(f"  CAGR: {best_stats['CAGR']:.2f}% (vs {s_base['CAGR']:.2f}%)")
    print(f"  Sharpe: {best_stats['Sharpe']:.2f} (vs {s_base['Sharpe']:.2f})")
    print(f"  Max DD: {best_stats['Max DD']:.2f}% (vs {s_base['Max DD']:.2f}%)")
    print(f"  Trades: {best_stats['Trades']} (vs {s_base['Trades']})")
    print(f"  Win Rate: {best_stats['Win Rate']:.1f}% (vs {s_base['Win Rate']:.1f}%)")
    print("="*80)

if __name__ == '__main__':
    main()
