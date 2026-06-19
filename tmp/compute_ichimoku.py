import os
import sys
import pandas as pd
import numpy as np

# Make sure the project root is in the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.data.db import SQLiteCache
from src.data.pipeline import standardize_and_validate
from src.signals.advanced_stochastic import AdvancedStochastic
from src.signals.kalman_rsi import KalmanRSI
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from src.signals.trend_strength import TrendStrengthIndex
from src.features.vif import calculate_vif

def main():
    print("Loading data from database...")
    cache = SQLiteCache("database/lttd.db")
    df = cache.load_dataframe()
    df = standardize_and_validate(df)
    
    print(f"Data loaded: {len(df)} rows from {df.index.min()} to {df.index.max()}")
    
    print("Computing active indicators...")
    stoch = AdvancedStochastic(dynamic_lookback=None).compute(df)
    rsi50 = KalmanRSI(dynamic_lookback=None).compute(df)
    fourier = AdaptiveFourierSupertrend(dynamic_lookback=None).compute(df)
    tsi = TrendStrengthIndex(dynamic_lookback=None).compute(df)
    
    print("Computing Ichimoku Cloud elements...")
    # 9-period high/low midpoint
    tenkan = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
    # 26-period high/low midpoint
    kijun = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
    # Senkou Span A (shifted 26 periods)
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    # Senkou Span B (52-period midpoint, shifted 26 periods)
    midpoint_52 = (df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2
    senkou_b = midpoint_52.shift(26)
    # Chikou Span (shifted backward 25 periods as in legacy Pinescript)
    chikou = df['close'].shift(-25)
    
    print("Creating Ichimoku feature candidates...")
    tenkan_kijun_diff = tenkan - kijun
    price_kijun_diff = df['close'] - kijun
    price_cloud_top_diff = df['close'] - np.maximum(senkou_a, senkou_b)
    price_cloud_bottom_diff = df['close'] - np.minimum(senkou_a, senkou_b)
    senkou_diff = senkou_a - senkou_b
    chikou_diff_causal = df['close'] - df['close'].shift(26)
    
    # Construct combined feature matrix
    feature_matrix = pd.DataFrame({
        "AdvancedStochastic": stoch,
        "RSI-50": rsi50,
        "FourierSupertrend": fourier,
        "TrendStrengthIndex": tsi,
        "tenkan_kijun_diff": tenkan_kijun_diff,
        "price_kijun_diff": price_kijun_diff,
        "price_cloud_top_diff": price_cloud_top_diff,
        "price_cloud_bottom_diff": price_cloud_bottom_diff,
        "senkou_diff": senkou_diff,
        "chikou_diff_causal": chikou_diff_causal
    }, index=df.index)
    
    # Analyze NaNs
    n_total = len(feature_matrix)
    feature_matrix_clean = feature_matrix.dropna()
    n_clean = len(feature_matrix_clean)
    print(f"Cleaned feature matrix: {n_clean} rows remaining after dropping NaNs (dropped {n_total - n_clean} rows).")
    
    print("Calculating Pearson correlation matrix...")
    corr_matrix = feature_matrix_clean.corr()
    
    # Correlation between Ichimoku candidates and active indicators
    active_cols = ["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex"]
    ichimoku_cols = [
        "tenkan_kijun_diff",
        "price_kijun_diff",
        "price_cloud_top_diff",
        "price_cloud_bottom_diff",
        "senkou_diff",
        "chikou_diff_causal"
    ]
    sub_corr_matrix = corr_matrix.loc[ichimoku_cols, active_cols]
    
    print("Calculating Variance Inflation Factor (VIF)...")
    vifs = calculate_vif(feature_matrix_clean)
    
    # Formulate report string
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("ICHIMOKU CLOUD AND ACTIVE INDICATORS COMPARATIVE ANALYSIS")
    report_lines.append("="*80)
    report_lines.append(f"Analysis Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Database Path: database/lttd.db")
    report_lines.append(f"Total Rows: {n_total} | Cleaned Rows: {n_clean} (Dropped {n_total - n_clean} due to lookbacks)")
    report_lines.append(f"Data Date Range: {feature_matrix_clean.index.min().strftime('%Y-%m-%d')} to {feature_matrix_clean.index.max().strftime('%Y-%m-%d')}")
    report_lines.append("\n" + "="*80)
    report_lines.append("1. VARIANCE INFLATION FACTOR (VIF) VALUES")
    report_lines.append("="*80)
    report_lines.append(f"{'Feature Name':<30} | {'VIF Value':<15} | {'Multicollinear (>10)?':<20}")
    report_lines.append("-" * 80)
    for col in feature_matrix.columns:
        vif_val = vifs[col]
        is_multicollinear = "YES" if vif_val > 10.0 else "NO"
        report_lines.append(f"{col:<30} | {vif_val:<15.4f} | {is_multicollinear:<20}")
    
    report_lines.append("\n" + "="*80)
    report_lines.append("2. PEARSON CORRELATION MATRIX (Sub-matrix: Ichimoku vs Active)")
    report_lines.append("="*80)
    # Format header
    header_str = f"{'Ichimoku Candidate':<30}"
    for act_col in active_cols:
        header_str += f" | {act_col[:18]:<18}"
    report_lines.append(header_str)
    report_lines.append("-" * 110)
    for ichi_col in ichimoku_cols:
        row_str = f"{ichi_col:<30}"
        for act_col in active_cols:
            val = sub_corr_matrix.loc[ichi_col, act_col]
            row_str += f" | {val:<18.4f}"
        report_lines.append(row_str)
        
    report_lines.append("\n" + "="*80)
    report_lines.append("3. FULL 10x10 PEARSON CORRELATION MATRIX")
    report_lines.append("="*80)
    # Format header
    header_str_full = f"{'Feature':<25}"
    for col in feature_matrix.columns:
        header_str_full += f" | {col[:12]:<12}"
    report_lines.append(header_str_full)
    report_lines.append("-" * 155)
    for row_col in feature_matrix.columns:
        row_str_full = f"{row_col:<25}"
        for col in feature_matrix.columns:
            val = corr_matrix.loc[row_col, col]
            row_str_full += f" | {val:<12.4f}"
        report_lines.append(row_str_full)
        
    report_lines.append("\n" + "="*80)
    report_lines.append("4. KEY FINDINGS & STRATEGIC RECOMMENDATIONS")
    report_lines.append("="*80)
    
    # Generate some simple automated insights to write to the file
    report_lines.append("- Multicollinearity Assessment:")
    high_vifs = vifs[vifs > 10.0]
    if len(high_vifs) > 0:
        report_lines.append(f"  * WARNING: {len(high_vifs)} features exhibit VIF > 10.0, indicating severe multicollinearity.")
        for col, val in high_vifs.items():
            report_lines.append(f"    - {col}: VIF = {val:.4f}")
        report_lines.append("  * Recommendation: These features cannot be added directly to the linear/ensemble consensus layer without PCA orthogonalization or step-wise pruning.")
    else:
        report_lines.append("  * SUCCESS: All features have VIF <= 10.0. No severe multicollinearity detected.")
        
    report_lines.append("\n- Correlation Assessment:")
    # Find highly correlated pairs (abs(corr) > 0.8)
    high_corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            col1 = corr_matrix.columns[i]
            col2 = corr_matrix.columns[j]
            c_val = corr_matrix.iloc[i, j]
            if abs(c_val) > 0.80:
                high_corr_pairs.append((col1, col2, c_val))
                
    if high_corr_pairs:
        report_lines.append("  * The following pairs exhibit very high correlation (|r| > 0.80):")
        for c1, c2, val in high_corr_pairs:
            report_lines.append(f"    - {c1} & {c2}: r = {val:.4f}")
    else:
        report_lines.append("  * No pairs exhibit very high correlation (|r| > 0.80).")
        
    report_text = "\n".join(report_lines)
    
    # Print to console
    print(report_text)
    
    # Save to file
    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ichimoku_stats.txt")
    with open(output_path, "w") as f:
        f.write(report_text)
    print(f"\nResults successfully written to {output_path}")

if __name__ == "__main__":
    main()
