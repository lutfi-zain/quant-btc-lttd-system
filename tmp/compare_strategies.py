import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, Any

# --- PORTED ICHIMOKU IDEATION MATHEMATICS (DO NOT ALTER LOGIC) ---

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def ehler_supersmoother(series: pd.Series, length: int = 7) -> pd.Series:
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(np.radians(1.414 * 180.0 / length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    vals = series.ffill().fillna(0).values
    filt = np.zeros(len(vals))
    filt[0] = vals[0]
    if len(vals) > 1:
        filt[1] = vals[1]
    for i in range(2, len(vals)):
        filt[i] = c1 * (vals[i] + vals[i-1]) / 2 + c2 * filt[i-1] + c3 * filt[i-2]
    return pd.Series(filt, index=series.index)

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

def generate_ichimoku_features(df: pd.DataFrame, p1=20, p2=60, p3=120, er_len=14, std_len=30, entropy_window=15, entropy_bins=6) -> pd.DataFrame:
    df = df.copy()
    df['ATR'] = compute_atr(df, p2)

    df['tenkan_sen'] = (df['High'].rolling(p1).max() + df['Low'].rolling(p1).min()) / 2
    df['kijun_sen'] = (df['High'].rolling(p2).max() + df['Low'].rolling(p2).min()) / 2

    df['senkou_span_a_raw'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    df['senkou_span_b_raw'] = (df['High'].rolling(p3).max() + df['Low'].rolling(p3).min()) / 2

    df['senkou_span_a'] = df['senkou_span_a_raw'].shift(p2)
    df['senkou_span_b'] = df['senkou_span_b_raw'].shift(p2)

    df['S_TK'] = np.tanh((df['tenkan_sen'] - df['kijun_sen']) / df['ATR'])

    cloud_max = np.maximum(df['senkou_span_a'], df['senkou_span_b'])
    cloud_min = np.minimum(df['senkou_span_a'], df['senkou_span_b'])
    dist_cloud = np.zeros(len(df))
    above = df['Close'] > cloud_max
    below = df['Close'] < cloud_min
    dist_cloud[above] = (df['Close'] - cloud_max)[above] / df['ATR'][above]
    dist_cloud[below] = (df['Close'] - cloud_min)[below] / df['ATR'][below]
    df['S_Cloud'] = np.tanh(dist_cloud)

    df['S_Future'] = np.tanh((df['senkou_span_a_raw'] - df['senkou_span_b_raw']) / df['ATR'])
    raw_chikou_dist = (df['Close'] - df['Close'].shift(p2)) / df['ATR']
    smoothed_chikou_dist = ehler_supersmoother(raw_chikou_dist, length=4)
    df['S_Chikou'] = np.tanh(smoothed_chikou_dist)

    imo_raw = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0

    df['IMO'] = ehler_supersmoother(imo_raw, length=7)
    df['IMO_Std'] = df['IMO'].rolling(std_len).std()

    change = df['Close'].diff().abs()
    volatility = change.rolling(er_len).sum()
    direction = df['Close'].diff(er_len).abs()
    df['ER'] = direction / volatility

    df['Entropy'] = shannon_entropy(df['Close'], window=entropy_window, bins=entropy_bins)

    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    # Hyper-tuned Denoising parameters
    CONFIRM_ENTRY = 2
    CONFIRM_EXIT = 1
    MIN_HOLD_DAYS = 10
    ER_ENTRY = 0.25
    T_ENTRY = 0.40
    CHIKOU_THRESH = -0.30
    IMMUNITY_THRESH = 0.50
    ENTROPY_THRESH = 2.271

    df = df.copy()
    pos = 0.0
    signals = []
    confirm_count = 0
    hold_days = 0
    intent = None

    for _, row in df.iterrows():
        imo = row['IMO']
        er = row['ER']
        std = row['IMO_Std']
        chikou = row.get('S_Chikou', 0.0)
        entropy = row.get('Entropy', 0.0)
        close = row['Close']
        cloud_a = row['senkou_span_a']
        cloud_b = row['senkou_span_b']

        if pd.isna(imo) or pd.isna(er) or pd.isna(std) or pd.isna(entropy):
            signals.append(pos)
            continue

        threshold = std * T_ENTRY

        if pos > 0:
            hold_days += 1
        else:
            hold_days = 0

        can_exit = hold_days >= MIN_HOLD_DAYS

        if pos == 0.0:
            cloud_min = np.minimum(cloud_a, cloud_b) if (not pd.isna(cloud_a) and not pd.isna(cloud_b)) else (cloud_a if not pd.isna(cloud_a) else (cloud_b if not pd.isna(cloud_b) else np.nan))
            gate_pass = True
            if not pd.isna(cloud_min):
                gate_pass = (close >= cloud_min)

            if imo > threshold and er > ER_ENTRY and entropy < ENTROPY_THRESH and gate_pass:
                if intent != 1.0:
                    intent = 1.0
                    confirm_count = 1
                else:
                    confirm_count += 1
                if confirm_count >= CONFIRM_ENTRY:
                    pos = 1.0
                    confirm_count = 0
                    hold_days = 0
                    intent = None
            else:
                intent = None
                confirm_count = 0

        else:  # pos == 1.0
            exit_signal = False
            if can_exit:
                if chikou < CHIKOU_THRESH and imo < IMMUNITY_THRESH:
                    exit_signal = True
                elif imo < 0:
                    exit_signal = True
            
            if exit_signal:
                if intent != 0.0:
                    intent = 0.0
                    confirm_count = 1
                else:
                    confirm_count += 1
                if confirm_count >= CONFIRM_EXIT:
                    pos = 0.0
                    confirm_count = 0
                    hold_days = 0
                    intent = None
            else:
                intent = None
                confirm_count = 0

        signals.append(pos)

    df['Pos'] = signals
    return df

# --- PERFORMANCE EVALUATION LOGIC ---

def run_sim(df: pd.DataFrame, position_col: str, tc_rate: float) -> pd.Series:
    """Simulate daily returns including transaction costs when position changes."""
    pos = df[position_col].astype(float)
    active_pos = pos.shift(1).fillna(0.0)
    market_ret = df['Close'].pct_change().fillna(0.0)
    
    # TC is paid on position changes
    pos_change = active_pos.diff().abs().fillna(0.0)
    tc = pos_change * tc_rate
    
    strat_ret = active_pos * market_ret - tc
    return strat_ret

def calculate_stats(ret_series: pd.Series, price_series: pd.Series, pos_series: pd.Series, start_date, end_date) -> Dict[str, Any]:
    years = (end_date - start_date).days / 365.25
    equity = (1 + ret_series).cumprod()
    
    # Geometric CAGR
    final_equity = equity.iloc[-1]
    cagr_val = (final_equity ** (1 / years) - 1) if final_equity > 0 else -1.0
    
    # Sharpe (annualized from daily returns)
    ann_factor = 365.25
    mean_ret = ret_series.mean()
    std_ret = ret_series.std()
    sharpe = (mean_ret / std_ret * np.sqrt(ann_factor)) if std_ret > 0 else 0.0
    
    # Sortino
    downside_ret = ret_series[ret_series < 0]
    downside_std = downside_ret.std()
    sortino = (mean_ret / downside_std * np.sqrt(ann_factor)) if downside_std > 0 else 0.0
    
    # Max DD
    peak = equity.cummax()
    dd = (equity - peak) / peak
    max_dd = dd.min()
    
    # Calmar
    calmar = cagr_val / abs(max_dd) if max_dd != 0 else float('inf')
    
    # Trade-level statistics
    # Count contiguous periods where position > 0
    in_pos = pos_series > 0
    starts = pos_series.index[(in_pos) & (~in_pos.shift(1).fillna(False))].tolist()
    ends = pos_series.index[(~in_pos) & (in_pos.shift(1).fillna(False))].tolist()
    
    if len(starts) > len(ends):
        ends.append(pos_series.index[-1])
        
    trades = []
    for s, e in zip(starts, ends):
        # Calculate compounded net return for the trade
        # Need to slice the returns during the trade period
        # Since active_pos is shifted by 1, the returns affected are from index s+1 to e
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
    # Load prices from main DB
    conn = sqlite3.connect("database/lttd.db")
    df_ohlcv = pd.read_sql(
        "SELECT timestamp, open as Open, high as High, low as Low, close as Close FROM ohlcv ORDER BY timestamp",
        conn,
        parse_dates=["timestamp"],
        index_col="timestamp"
    )
    
    # Load LTTD system signals
    df_lttd = pd.read_sql(
        "SELECT date, target_exposure, final_score FROM daily_lttd ORDER BY date",
        conn,
        parse_dates=["date"],
        index_col="date"
    )
    conn.close()
    
    print(f"Loaded {len(df_ohlcv)} daily price rows. Date range: {df_ohlcv.index.min().date()} to {df_ohlcv.index.max().date()}")
    print(f"Loaded {len(df_lttd)} LTTD signal rows. Date range: {df_lttd.index.min().date()} to {df_lttd.index.max().date()}")
    
    # Align datasets on overlap
    # We will compute Ichimoku features on df_ohlcv
    df_ich = generate_ichimoku_features(df_ohlcv)
    df_ich = generate_signals(df_ich)
    
    # Align both dataframes on the date range of LTTD signals to ensure fair comparison
    common_idx = df_lttd.index.intersection(df_ich.index)
    print(f"Common date range for comparison: {common_idx.min().date()} to {common_idx.max().date()} ({len(common_idx)} days)")
    
    df_comp = pd.DataFrame(index=common_idx)
    df_comp['Close'] = df_ohlcv.loc[common_idx, 'Close']
    df_comp['LTTD_Pos'] = df_lttd.loc[common_idx, 'target_exposure']
    df_comp['Ichimoku_Pos'] = df_ich.loc[common_idx, 'Pos']
    
    start_date = common_idx.min()
    end_date = common_idx.max()
    
    tc_scenarios = [0.0, 0.0005, 0.001, 0.002]
    
    results = []
    for tc in tc_scenarios:
        # Run LTTD
        ret_lttd = run_sim(df_comp, 'LTTD_Pos', tc)
        stats_lttd = calculate_stats(ret_lttd, df_comp['Close'], df_comp['LTTD_Pos'], start_date, end_date)
        
        # Run Ichimoku
        ret_ich = run_sim(df_comp, 'Ichimoku_Pos', tc)
        stats_ich = calculate_stats(ret_ich, df_comp['Close'], df_comp['Ichimoku_Pos'], start_date, end_date)
        
        results.append((tc, stats_lttd, stats_ich))
        
    # Print comparison table
    print("\n" + "="*80)
    print(f"STRATEGY PERFORMANCE COMPARISON ({start_date.date()} to {end_date.date()})")
    print("="*80)
    
    # Buy & Hold stats
    bh_ret = df_comp['Close'].pct_change().fillna(0.0)
    bh_eq = (1 + bh_ret).cumprod()
    bh_years = (end_date - start_date).days / 365.25
    bh_cagr = (bh_eq.iloc[-1] ** (1 / bh_years) - 1) * 100
    bh_max_dd = ((bh_eq - bh_eq.cummax()) / bh_eq.cummax()).min() * 100
    bh_sharpe = bh_ret.mean() / bh_ret.std() * np.sqrt(365.25)
    print(f"Buy & Hold BTC  | CAGR: {bh_cagr:.2f}% | Max DD: {bh_max_dd:.2f}% | Sharpe: {bh_sharpe:.2f} | Return: {(bh_eq.iloc[-1]-1)*100:,.2f}%")
    print("-"*80)
    
    for tc, s_lttd, s_ich in results:
        print(f"TRANSACTION COST: {tc*10000:.0f} bps ({tc*100:.2f}%)")
        print(f"  LTTD System:")
        print(f"    Total Return: {s_lttd['Total Return']:,.2f}% | CAGR: {s_lttd['CAGR']:.2f}% | Sharpe: {s_lttd['Sharpe']:.2f} | Sortino: {s_lttd['Sortino']:.2f}")
        print(f"    Max DD: {s_lttd['Max DD']:.2f}% | Calmar: {s_lttd['Calmar']:.2f} | Trades: {s_lttd['Trades']} | Win Rate: {s_lttd['Win Rate']:.1f}%")
        print(f"  Ichimoku Ideation System:")
        print(f"    Total Return: {s_ich['Total Return']:,.2f}% | CAGR: {s_ich['CAGR']:.2f}% | Sharpe: {s_ich['Sharpe']:.2f} | Sortino: {s_ich['Sortino']:.2f}")
        print(f"    Max DD: {s_ich['Max DD']:.2f}% | Calmar: {s_ich['Calmar']:.2f} | Trades: {s_ich['Trades']} | Win Rate: {s_ich['Win Rate']:.1f}%")
        
        # Calculate ratio of CAGR and Sharpe
        cagr_ratio = s_ich['CAGR'] / s_lttd['CAGR'] if s_lttd['CAGR'] != 0 else 0
        sharpe_ratio = s_ich['Sharpe'] / s_lttd['Sharpe'] if s_lttd['Sharpe'] != 0 else 0
        total_ret_ratio = s_ich['Total Return'] / s_lttd['Total Return'] if s_lttd['Total Return'] != 0 else 0
        
        print(f"  Comparison (Ichimoku / LTTD):")
        print(f"    Total Return Ratio: {total_ret_ratio:.2f}x")
        print(f"    CAGR Ratio        : {cagr_ratio:.2f}x")
        print(f"    Sharpe Ratio      : {sharpe_ratio:.2f}x")
        print("-"*80)

if __name__ == '__main__':
    main()
