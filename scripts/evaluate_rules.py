import sqlite3
import pandas as pd
import numpy as np
from src.data.valuation_api_client import ValuationApiClient

def calc_exposure(score, regime, comp, prev, onchain=None):
    exposure = prev
    
    # Base trend
    if score >= 0.396:
        exposure = 1.0
    elif score <= 0.371:
        exposure = 0.0
        
    # Bear
    if regime == "BEAR":
        exposure = 0.0
        
    # Value Scaling In
    if comp >= 0.907:
        exposure = max(exposure, 0.5)
        
    # Value Scaling Out
    if comp <= -0.935:
        exposure = min(exposure, 0.5)
            
    if comp <= -2.444:
        exposure = 0.0
        
    if onchain is not None and exposure > 0:
        sth_nupl = onchain.get("sth_nupl", 0.0)
        sth_mvrv = onchain.get("sth_mvrv", 0.0)
        if sth_nupl > 0.75 or sth_mvrv > 2.0:
            exposure = min(exposure, 0.5)
            
    return exposure

def main():
    conn = sqlite3.connect("database/lttd.db")
    df = pd.read_sql("""
        SELECT d.date, d.regime, d.final_score as score, o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """, conn)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    df["simple_return"] = df["close"].pct_change().fillna(0.0)
    
    val_client = ValuationApiClient()
    val_client.get_composite_value_for_date(pd.Timestamp("2026-01-01", tz="UTC"))
    val_df = val_client._historical_cache
    if val_df is not None:
        val_df["date"] = pd.to_datetime(val_df["date"]).dt.tz_convert(None)
        val_df.set_index("date", inplace=True)
        df = df.join(val_df, how="left")
        
    df["composite_value"] = df["composite_value"].fillna(0.0)
    
    # We don't have onchain in this df easily, but we can just test the base parameters.
    
    exposures = []
    prev = 0.0
    for t, row in df.iterrows():
        exp = calc_exposure(row["score"], row["regime"], row["composite_value"], prev)
        exposures.append(exp)
        prev = exp
        
    df["exposure"] = exposures
    df["position"] = np.sign(df["score"]) * df["exposure"].abs()
    df["strat_return"] = df["position"].shift(1).fillna(0.0) * df["simple_return"]
    df["equity"] = (1 + df["strat_return"]).cumprod()
    
    years = (df.index.max() - df.index.min()).days / 365.25
    cagr = (df["equity"].iloc[-1] ** (1 / years) - 1) * 100
    
    peak = df["equity"].cummax()
    dd = (df["equity"] - peak) / peak
    max_dd = dd.min() * 100
    
    print(f"Strategy Return: {(df['equity'].iloc[-1] - 1) * 100:.2f}%")
    print(f"Strategy CAGR: {cagr:.2f}%")
    print(f"Max DD: {max_dd:.2f}%")

if __name__ == "__main__":
    main()
