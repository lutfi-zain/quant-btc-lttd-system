import argparse
import sys
import os
import concurrent.futures
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import vectorbt as vbt

# Ensure the current directory is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.data.pipeline import ohlcv_pipeline
from src.signals.onchain import OnChainFeed
from src.backtest.wfo import WFOIterator, point_in_time_join
from src.regime.hmm import train_hmm, infer_regime
from src.features.builder import FeatureMatrixBuilder
from src.ensemble.wfo import WFOEnsemble
from src.execution.sizing import calculate_target_exposure
from src.regime.filter import apply_onchain_overrides


class MockExecutionAdapter:
    """
    Bypasses Layer 5 SQLite operations during backtesting.
    Collects daily execution metrics in memory and returns them as a pandas DataFrame.
    """
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.previous_regime: Optional[str] = None
        self.transitions: List[Dict[str, Any]] = []

    def run(
        self,
        date_str: str,
        final_score: float,
        regime: str,
        posteriors: Optional[Dict[str, float]] = None,
        log_return: float = 0.0,
        realized_volatility: float = 0.0,
    ) -> Dict[str, Any]:
        regime_upper = regime.upper()
        target_exposure = calculate_target_exposure(final_score, regime_upper)
        
        # Calculate transition (in-memory)
        transition_occurred = False
        if self.previous_regime is not None and self.previous_regime != regime_upper:
            transition_occurred = True
            posteriors_clean = posteriors or {"BULL": 0.0, "BEAR": 0.0, "SIDEWAYS": 0.0}
            self.transitions.append({
                "date": date_str,
                "from_regime": self.previous_regime,
                "to_regime": regime_upper,
                "posterior": posteriors_clean.get(regime_upper, 0.0),
                "log_return": log_return,
                "realized_volatility": realized_volatility,
            })
            
        self.previous_regime = regime_upper
        
        record = {
            "date": date_str,
            "regime": regime_upper,
            "final_score": final_score,
            "target_exposure": target_exposure,
            "transition_occurred": transition_occurred,
        }
        self.records.append(record)
        return record

    def get_dataframe(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame()
        df = pd.DataFrame(self.records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df


def _run_fold(
    train_idx: pd.DatetimeIndex,
    val_idx: pd.DatetimeIndex,
    test_idx: pd.DatetimeIndex,
    df_merged: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    y: pd.Series,
    ensemble_mode: str = "pca_consensus"
) -> List[Dict[str, Any]]:
    """
    Worker function to execute a single WFO fold.
    """
    # 1. Train HMM on train_idx close prices
    close_train = df_merged.loc[train_idx, "close"]
    hmm_model, state_to_regime = train_hmm(close_train, window=21)
    
    # 2. Predict HMM regime and posteriors for test_idx (day-by-day, causally)
    test_regimes = []
    test_posteriors = []
    full_close = df_merged["close"]
    
    for date in test_idx:
        close_up_to_date = full_close.loc[:date]
        if len(close_up_to_date) < 120:
            test_regimes.append("SIDEWAYS")
            test_posteriors.append({"BULL": 0.0, "BEAR": 0.0, "SIDEWAYS": 1.0})
            continue
        res = infer_regime(hmm_model, state_to_regime, close_up_to_date, window=21)
        test_regimes.append(res["regime"])
        test_posteriors.append(res["posteriors"])
        
    # 3. Fit FeatureProcessor on train_idx, transform both train_idx and test_idx
    from src.features.processor import FeatureProcessor
    processor = FeatureProcessor()
    
    X_train = feature_matrix.loc[train_idx]
    y_train = y.loc[train_idx]
    X_test = feature_matrix.loc[test_idx]
    
    processor.fit(X_train, y_train)
    X_train_proc = processor.transform(X_train)
    X_test_proc = processor.transform(X_test)
    
    # 4. Fit ensemble and 5. Predict Final Score
    if ensemble_mode == "pca_consensus":
        from src.ensemble.model import PCAConsensusEnsemble
        model = PCAConsensusEnsemble()
        if processor.pca is not None:
            model.fit(
                X=X_train,
                pca_components_matrix=processor.pca.pca.components_,
                kept_cols=processor.kept_tech_cols
            )
            test_scores = model.predict(X_test)
        else:
            model.fit(X=X_train)
            test_scores = model.predict(X_test)
    else:
        from src.ensemble.model import L1LassoEnsemble
        model = L1LassoEnsemble()
        model.fit(X_train_proc, y_train)
        test_scores = model.predict(X_test_proc)
    
    # 6. Run simulated daily execution pipeline (MockExecutionAdapter)
    adapter = MockExecutionAdapter()
    fold_records = []
    
    # Use returns/volatility from raw data for transitioning telemetry
    log_returns_series = np.log(df_merged["close"] / df_merged["close"].shift(1)).fillna(0.0)
    realized_vol_series = log_returns_series.rolling(21).std().fillna(0.0)
    
    for i, date in enumerate(test_idx):
        date_str = date.strftime("%Y-%m-%d")
        score = float(test_scores.loc[date])
        regime = test_regimes[i]
        posteriors_dict = test_posteriors[i]
        
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            if col in df_merged.columns:
                val = df_merged.loc[date, col]
                onchain_metrics[col] = float(val) if not pd.isna(val) else 0.0
            else:
                onchain_metrics[col] = 0.0
                
        overridden_posteriors = apply_onchain_overrides(posteriors_dict, onchain_metrics)
        
        final_regime = max(overridden_posteriors, key=overridden_posteriors.get)
                
        log_ret = float(log_returns_series.loc[date])
        realized_vol = float(realized_vol_series.loc[date])
        
        res_record = adapter.run(
            date_str=date_str,
            final_score=score,
            regime=final_regime,
            posteriors=overridden_posteriors,
            log_return=log_ret,
            realized_volatility=realized_vol
        )
        
        res_record["date"] = date
        res_record["close"] = float(df_merged.loc[date, "close"])
        fold_records.append(res_record)
        
    return fold_records


class BacktestRunner:
    def __init__(self, legacy_fixed_window: bool = False, ensemble_mode: str = "pca_consensus"):
        self.legacy_fixed_window = legacy_fixed_window
        self.ensemble_mode = ensemble_mode

    def run(self, data: pd.DataFrame) -> dict:
        """
        Runs the full walk-forward backtest optimization.
        """
        # 1. Calibrate OU half-life (dynamic lookback)
        wfo_ens = WFOEnsemble()
        log_returns = np.log(data["close"] / data["close"].shift(1)).fillna(0.0)
        
        dynamic_lookback = wfo_ens.run_wfo_calibration(
            log_returns,
            data.index[0],
            data.index[-1],
            legacy_fixed_window=self.legacy_fixed_window
        )
        
        # 2. Build feature matrix
        builder = FeatureMatrixBuilder(dynamic_lookback=dynamic_lookback)
        feature_matrix = builder.build_matrix(data).dropna()
        
        # Align index
        common_idx = data.index.intersection(feature_matrix.index).sort_values()
        df_merged = data.loc[common_idx]
        feature_matrix = feature_matrix.loc[common_idx]
        
        # Define target y (next-day binary class [0, 1])
        price_diff = df_merged["close"].shift(-1) - df_merged["close"]
        y = np.sign(price_diff).fillna(1.0).map({-1.0: 0, 0.0: 0, 1.0: 1})
        y = y.loc[common_idx]
        
        # 3. Generate WFO folds (3yr train -> 6mo val -> 6mo test)
        iterator = WFOIterator(purge_days=350)
        folds = list(iterator.generate_wfo_folds(common_idx))
        
        if not folds:
            # Fallback: single training run on all data if not enough history
            print("⚠ Warning: Insufficient data for 3-year WFO splits. Running fallback single fit.")
            records = _run_fold(common_idx, common_idx, common_idx, df_merged, feature_matrix, y, ensemble_mode=self.ensemble_mode)
        else:
            # 4. Parallelize independent WFO fold computations
            records = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for train_idx, val_idx, test_idx in folds:
                    futures.append(
                        executor.submit(
                            _run_fold,
                            train_idx,
                            val_idx,
                            test_idx,
                            df_merged,
                            feature_matrix,
                            y,
                            ensemble_mode=self.ensemble_mode
                        )
                    )
                for future in concurrent.futures.as_completed(futures):
                    records.extend(future.result())
                    
        # Sort records chronologically
        records = sorted(records, key=lambda x: x["date"])
        
        # Convert to DataFrame
        results_df = pd.DataFrame(records).set_index("date")
        results_df = results_df[~results_df.index.duplicated(keep="first")]
        
        # 5. Compute vectorbt portfolio state
        close_series = results_df["close"]
        exposure = results_df["target_exposure"]
        
        # targetpercent expects portfolio weights. target_exposure acts directly as portfolio weight.
        portfolio = vbt.Portfolio.from_orders(
            close_series,
            size=exposure,
            size_type='targetpercent',
            init_cash=10000.0,
            fees=0.001
        )
        
        # Calculate performance metrics
        total_return = portfolio.total_return()
        
        # Annualized Sharpe Ratio: vectorbt calculates this directly, but let's calculate annualized Sharpe on returns
        daily_returns = portfolio.returns()
        mean_ret = daily_returns.mean()
        std_ret = daily_returns.std()
        sharpe = (mean_ret / std_ret * np.sqrt(365)) if std_ret > 0 else 0.0
        
        max_drawdown = portfolio.max_drawdown()
        
        # Hit rate (win rate) Partitioned by HMM Regime
        # Win is defined as positive daily return when active exposure is non-zero
        regime_metrics = {}
        for regime_name in ["BULL", "BEAR", "SIDEWAYS"]:
            regime_df = results_df[results_df["regime"] == regime_name]
            if len(regime_df) > 0:
                # Active days (where exposure > 0)
                active_days = daily_returns.loc[regime_df.index.intersection(daily_returns.index)]
                non_zero_days = active_days[results_df.loc[active_days.index, "target_exposure"] > 0]
                
                if len(non_zero_days) > 0:
                    wins = (non_zero_days > 0).sum()
                    hit_rate = float(wins / len(non_zero_days))
                else:
                    hit_rate = 0.0
                regime_metrics[regime_name] = {
                    "count": len(regime_df),
                    "active_days": len(non_zero_days),
                    "hit_rate": hit_rate
                }
            else:
                regime_metrics[regime_name] = {"count": 0, "active_days": 0, "hit_rate": 0.0}
                
        return {
            "status": "success",
            "legacy_fixed_window": self.legacy_fixed_window,
            "results": results_df,
            "metrics": {
                "total_return": total_return,
                "annualized_sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "regime_metrics": regime_metrics
            }
        }


def main():
    parser = argparse.ArgumentParser(description="LTTD WFO Backtest Runner")
    parser.add_argument(
        "--ensemble-mode",
        type=str,
        default="pca_consensus",
        choices=["pca_consensus", "lasso"],
        help="Choose ensemble aggregation mode: 'pca_consensus' (Option A) or 'lasso' (Option B)",
    )
    parser.add_argument(
        "--legacy-fixed-window",
        action="store_true",
        help="Force a static 200-day lookback window for all technical indicators",
    )
    parser.add_argument("--start", type=str, default="2017-01-01", help="Start date")
    parser.add_argument("--end", type=str, default="2026-06-01", help="End date")

    args = parser.parse_args()

    print(f"Loading daily BTC OHLCV from Binance...")
    df_ohlcv = ohlcv_pipeline()
    
    print(f"Loading historical on-chain metrics from BRK API...")
    feed = OnChainFeed()
    onchain = feed.fetch_historical_bulk(start=-2500)
    
    print(f"Joining datasets causally...")
    df_merged = point_in_time_join(df_ohlcv, onchain)
    
    # Filter by date range
    df_merged = df_merged.loc[args.start:args.end]
    print(f"Available data rows for backtest: {len(df_merged)}")
    
    runner = BacktestRunner(legacy_fixed_window=args.legacy_fixed_window, ensemble_mode=args.ensemble_mode)
    res = runner.run(df_merged)
    
    metrics = res["metrics"]
    print("\n==========================================================================")
    print("                      LTTD SYSTEM - BACKTEST RESULTS                      ")
    print("==========================================================================")
    print(f"Total Return             : {metrics['total_return']:.2%}")
    print(f"Annualized Sharpe Ratio  : {metrics['annualized_sharpe']:.4f}")
    print(f"Max Drawdown             : {metrics['max_drawdown']:.2%}")
    print("\nRegime Partitioned Metrics:")
    for regime, r_met in metrics["regime_metrics"].items():
        print(f"  → {regime:10}: Total Days={r_met['count']:<5} Active Days={r_met['active_days']:<5} Hit Rate={r_met['hit_rate']:.2%}")
    print("==========================================================================")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
