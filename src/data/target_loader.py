import pandas as pd
from pathlib import Path

REGIME_MAPPING = {
    "Strong Bull": 1.0,
    "Weak Bull": 0.75,
    "Neutral": 0.50,
    "Weak Bear": 0.25,
    "Strong Bear": 0.0
}

def load_and_forward_fill_targets(csv_path: str | Path, start_date: str = None, end_date: str = None) -> pd.Series:
    """
    Loads sparse regime targets from CSV, maps them to [0, 1] intensities,
    and forward-fills to create a daily continuous target series.
    """
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Map regimes to intensities
    df['RegimeIntensity'] = df['Regime'].map(REGIME_MAPPING)
    
    if df['RegimeIntensity'].isnull().any():
        missing = df[df['RegimeIntensity'].isnull()]['Regime'].unique()
        raise ValueError(f"Unknown regimes found in target CSV: {missing}")
        
    df.set_index('Date', inplace=True)
    df = df.sort_index()
    
    # Create daily date range
    first_date = df.index.min()
    if start_date is not None:
        first_date = min(first_date, pd.to_datetime(start_date))
        
    last_date = df.index.max()
    if end_date is not None:
        last_date = max(last_date, pd.to_datetime(end_date))
        
    if pd.isna(first_date) or pd.isna(last_date):
        return pd.Series(dtype=float, name="RegimeIntensity")
        
    # We must ensure we cover from first_date to last_date.
    daily_idx = pd.date_range(start=first_date, end=last_date, freq='D')
    
    # Combine the original index with the daily index to ensure we don't miss any intra-day (if any, though they should be daily)
    combined_idx = df.index.union(daily_idx).sort_values()
    
    # Reindex and forward fill
    filled_series = df['RegimeIntensity'].reindex(combined_idx).ffill()
    
    # Slice to exact daily index required
    if start_date is not None and end_date is not None:
        filled_series = filled_series.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]
        # ensure strict daily freq
        filled_series = filled_series.asfreq('D')
        
    return filled_series

def validate_target_alignment(y: pd.Series, X: pd.DataFrame) -> None:
    """
    Validates that the target series y perfectly aligns with feature dataframe X,
    and checks for NaN gaps.
    """
    if not y.index.equals(X.index):
        raise ValueError("Target index does not match Feature index. Misalignment detected.")
        
    if y.isnull().any():
        raise ValueError("Target series contains NaN values (gaps).")

def load_regime_targets(index: pd.DatetimeIndex, csv_path: str | Path = None) -> pd.Series:
    """
    Convenience function to load and forward fill the ISP regime targets,
    and align exactly to the provided DatetimeIndex.
    """
    if csv_path is None:
        csv_path = Path(__file__).resolve().parent.parent.parent / "docs" / "isps" / "isp-regimes-btcusd-2026-06-13.csv"
        
    # Standardize index timezone if any
    start_date = index.min().strftime("%Y-%m-%d") if not index.empty else None
    end_date = index.max().strftime("%Y-%m-%d") if not index.empty else None
    
    y = load_and_forward_fill_targets(csv_path, start_date=start_date, end_date=end_date)
    
    # Ensure index alignment and timezone match
    if y.index.tz is None and index.tz is not None:
        y.index = y.index.tz_localize("UTC")
    elif y.index.tz is not None and index.tz is None:
        y.index = y.index.tz_localize(None)
        
    y = y.reindex(index).ffill().bfill()
    return y
