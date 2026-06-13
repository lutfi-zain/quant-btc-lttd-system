import pandas as pd
import numpy as np
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.data.pipeline import ohlcv_pipeline
from src.data.brk_ingestion_service import BRKIngestionService
from src.regime.hmm import train_hmm, infer_regime_history
from src.regime.filter import apply_onchain_overrides

def load_isp(filepath):
    df = pd.read_csv(filepath, parse_dates=['Date'])
    df['Date'] = df['Date'].dt.tz_localize('UTC')
    df = df.set_index('Date')
    return df

def main():
    print("Loading ISP...")
    isp_df = load_isp("isp-regimes-btcusd-2026-06-12.csv")
    
    print("Fetching historical price data...")
    end_time = datetime(2026, 6, 12, tzinfo=timezone.utc)
    ohlcv = ohlcv_pipeline(end_time=end_time)
    if ohlcv.index.tzinfo is None:
        ohlcv.index = pd.to_datetime(ohlcv.index).tz_localize('UTC')
    else:
        ohlcv.index = pd.to_datetime(ohlcv.index).tz_convert('UTC')
    
    print("Fetching historical on-chain data...")
    brk = BRKIngestionService(base_url="https://bitview.space")
    # Fetch historical lookback for the earliest ISP date
    onchain = brk.fetch_historical(lookback_days=4000) 
    
    # Run HMM on the whole history
    print("Training HMM on full history to evaluate fit...")
    model, state_to_regime = train_hmm(ohlcv['close'], window=21)
    print("State to regime mapping:", state_to_regime)
    
    regime_hist = infer_regime_history(model, state_to_regime, ohlcv['close'], window=21)
    
    # Merge and compare
    combined = isp_df.join(regime_hist, how='inner')
    
    # Evaluate matches
    print("\n--- Evaluation at ISP Transition Dates ---")
    matches = 0
    total = 0
    
    for date, row in combined.iterrows():
        isp_reg = row['Regime']
        hmm_reg = row['regime']
        
        # Apply on-chain overrides for this specific date
        onchain_data = onchain[onchain.index <= date]
        if not onchain_data.empty:
            latest_onchain = onchain_data.iloc[-1].to_dict()
            posteriors = {
                "BULL": row['p_bull'],
                "BEAR": row['p_bear'],
                "SIDEWAYS": row['p_sideways']
            }
            overridden = apply_onchain_overrides(posteriors, latest_onchain)
            final_regime = max(overridden, key=overridden.get)
        else:
            final_regime = hmm_reg
            overridden = {}
        
        print(f"{date.date()} | ISP: {isp_reg:<12} | HMM: {hmm_reg:<8} | Filtered: {final_regime:<8} | MVRV: {latest_onchain.get('sth_mvrv',0):.2f}")
        
        # Mapping for evaluation
        # Let's consider Strong Bull / Weak Bull as BULL
        # Strong Bear / Weak Bear as BEAR
        # Neutral as SIDEWAYS
        if 'Bull' in isp_reg and final_regime == 'BULL':
            matches += 1
        elif 'Bear' in isp_reg and final_regime == 'BEAR':
            matches += 1
        elif 'Neutral' in isp_reg and final_regime == 'SIDEWAYS':
            matches += 1
        total += 1
        
    print(f"\nAccuracy (Simplified): {matches}/{total} ({(matches/total)*100:.2f}%)")

if __name__ == '__main__':
    main()
