import os
import sys
import pandas as pd
import numpy as np

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.data.pipeline import ohlcv_pipeline
from src.signals.onchain import OnChainFeed
from src.backtest.wfo import point_in_time_join
from src.backtest.runner import BacktestRunner
import src.regime.hmm as hmm_module

# Load price and on-chain datasets
print("Loading daily BTC OHLCV from Binance...")
df_ohlcv = ohlcv_pipeline()
print("Loading historical on-chain metrics from BRK API...")
feed = OnChainFeed()
onchain = feed.fetch_historical_bulk(start=-4500)
print("Joining datasets causally...")
df_merged = point_in_time_join(df_ohlcv, onchain)

# We will test spans: 1 (baseline), 5, 10, 15, 20
for span in [1, 5, 10, 15, 20]:
    print(f"\n==========================================================")
    print(f"Testing HMM Posterior Smoothing: ema_span = {span}")
    print(f"==========================================================")
    
    # Monkey-patch HMM inference default arguments
    original_infer_regime = hmm_module.infer_regime
    original_infer_regime_history = hmm_module.infer_regime_history
    
    hmm_module.infer_regime = lambda model, state_to_regime, close, window=21, ema_span=span: \
        original_infer_regime(model, state_to_regime, close, window, ema_span=span)
        
    hmm_module.infer_regime_history = lambda model, state_to_regime, close, window=21, ema_span=span: \
        original_infer_regime_history(model, state_to_regime, close, window, ema_span=span)
        
    try:
        runner = BacktestRunner(ensemble_mode="xgboost")
        res = runner.run(df_merged)
        
        # Slices to 2017-01-01 to 2025-01-01 to compare with baseline exactly
        results_df = res["results"].loc["2017-01-01":"2025-01-01"]
        close_series = results_df["close"]
        exposure = results_df["target_exposure"]
        
        import vectorbt as vbt
        portfolio = vbt.Portfolio.from_orders(
            close_series,
            size=exposure,
            size_type='targetpercent',
            init_cash=10000.0,
            fees=0.001
        )
        
        # Calculate transition statistics on HMM regimes (not the score-based final_regime)
        # Note that inside runner.py, regime column of results_df stores final_regime (which is mapped from score).
        # But we also have test_regimes which is HMM predicted regime. Let's see if we can calculate transitions on final_regime.
        # final_regime is mapped from score, but score is trained on target y, which uses HMM regimes as labels!
        # So smoothing HMM regimes will change the target labels y and therefore train a different score model.
        results_df["regime_shifted"] = results_df["regime"].shift(1)
        transitions = len(results_df[results_df["regime"] != results_df["regime_shifted"]]) - 1
        lengths = results_df.groupby((results_df["regime"] != results_df["regime"].shift()).cumsum()).size()
        
        daily_returns = portfolio.returns()
        mean_ret = daily_returns.mean()
        std_ret = daily_returns.std()
        sharpe = (mean_ret / std_ret * np.sqrt(365)) if std_ret > 0 else 0.0
        
        print(f"Total Return             : {portfolio.total_return()*100:.2f}%")
        print(f"Annualized Sharpe Ratio  : {sharpe:.4f}")
        print(f"Max Drawdown             : {portfolio.max_drawdown()*100:.2f}%")
        print(f"Final Regime Transitions : {transitions} (Median Segment: {lengths.median():.1f} days)")
        
    finally:
        # Restore original functions
        hmm_module.infer_regime = original_infer_regime
        hmm_module.infer_regime_history = original_infer_regime_history
