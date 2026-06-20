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
        self.previous_exposure: Optional[float] = None
        self.previous_circuit_breaker_active: bool = False
        self.transitions: List[Dict[str, Any]] = []
        self.days_since_exit = 999
        self.days_in_position = 0

    def run(
        self,
        date_str: str,
        final_score: float,
        regime: str,
        posteriors: Optional[Dict[str, float]] = None,
        onchain_metrics: Optional[Dict[str, float]] = None,
        log_return: float = 0.0,
        realized_volatility: float = 0.0,
        composite_value: float = 0.0,
        price: Optional[float] = None,
        ma_val: Optional[float] = None,
        entropy_val: Optional[float] = None,
        er_val: Optional[float] = None,
        cloud_min: Optional[float] = None,
    ) -> Dict[str, Any]:
        from src.execution.sizing import (
            calculate_target_exposure,
            super_smoother,
            SUPERSMOOTHER_PERIOD_ENTRY,
            SUPERSMOOTHER_PERIOD_EXIT,
        )
        
        # Track timers
        if self.previous_exposure is not None and self.previous_exposure >= 0.9:
            self.days_in_position += 1
            self.days_since_exit = 0
        else:
            self.days_in_position = 0
            self.days_since_exit += 1
            
        # Calculate SuperSmoother smoothed scores using historical raw scores in self.records
        past_scores = [r["final_score"] for r in self.records]
        all_scores = past_scores + [final_score]
        scores_series = pd.Series(all_scores)
        
        smoothed_entry = float(super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_ENTRY).iloc[-1])
        smoothed_exit = float(super_smoother(scores_series, period=SUPERSMOOTHER_PERIOD_EXIT).iloc[-1])

        regime_upper = regime
        target_exposure, is_cb_active = calculate_target_exposure(
            smoothed_score_entry=smoothed_entry,
            smoothed_score_exit=smoothed_exit,
            vol=realized_volatility,
            regime=regime_upper,
            prev_exposure=self.previous_exposure,
            onchain_metrics=onchain_metrics,
            composite_value=composite_value,
            prev_circuit_breaker_active=self.previous_circuit_breaker_active,
            days_since_exit=self.days_since_exit,
            days_in_position=self.days_in_position,
            price=price,
            ma_val=ma_val,
            entropy_val=entropy_val,
            er_val=er_val,
            cloud_min=cloud_min
        )
        self.previous_exposure = target_exposure
        self.previous_circuit_breaker_active = is_cb_active
        
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
    test_posteriors = []
    full_close = df_merged["close"]
    
    for date in test_idx:
        close_up_to_date = full_close.loc[:date]
        if len(close_up_to_date) < 200:
            raw_post = {"BULL": 0.0, "BEAR": 0.0, "SIDEWAYS": 1.0}
        else:
            res_feat = infer_regime(hmm_model, state_to_regime, close_up_to_date, window=21, ema_span=1)
            raw_post = res_feat["posteriors"]
        test_posteriors.append(raw_post)
        
    # Get training posteriors for EMA warm-up (already overridden)
    from src.regime.hmm import infer_regime_history
    df_train_hmm = infer_regime_history(hmm_model, state_to_regime, close_train, window=21, ema_span=1)
    
    warmup_posteriors = []
    if not df_train_hmm.empty:
        warmup_subset = df_train_hmm.tail(50)
        for d, row in warmup_subset.iterrows():
            train_raw = {
                "BULL": row["p_bull"],
                "BEAR": row["p_bear"],
                "SIDEWAYS": row["p_sideways"]
            }
            train_onchain = {}
            for col in ["sth_mvrv", "sth_nupl"]:
                if col in df_merged.columns:
                    val = df_merged.loc[d, col]
                    train_onchain[col] = float(val) if not pd.isna(val) else 0.0
                else:
                    train_onchain[col] = 0.0
            train_overridden = apply_onchain_overrides(train_raw, train_onchain)
            warmup_posteriors.append(train_overridden)
            
    # Apply overrides to test posteriors immediately to build consistent sequence for smoothing
    overridden_test_posteriors = []
    for i, date in enumerate(test_idx):
        raw_post = test_posteriors[i]
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            if col in df_merged.columns:
                val = df_merged.loc[date, col]
                onchain_metrics[col] = float(val) if not pd.isna(val) else 0.0
            else:
                onchain_metrics[col] = 0.0
        overridden = apply_onchain_overrides(raw_post, onchain_metrics)
        overridden_test_posteriors.append(overridden)
        
    # Combine warmup and test overridden posteriors, and causally smooth them across days
    combined_posteriors = warmup_posteriors + overridden_test_posteriors
    df_combined = pd.DataFrame(combined_posteriors)
    df_combined_smoothed = df_combined.ewm(span=20, adjust=False).mean()
    
    # Slice back to only the test portion
    df_test_smoothed = df_combined_smoothed.tail(len(test_idx))
    
    test_posteriors_smoothed = []
    test_regimes = []
    for idx, row in df_test_smoothed.iterrows():
        post_dict = row.to_dict()
        test_posteriors_smoothed.append(post_dict)
        test_regimes.append(max(post_dict, key=post_dict.get))
        
    # 3. Add HMM posteriors to feature_matrix (locally within the fold to avoid lookahead leak)
    feature_matrix_fold = feature_matrix.copy()
    
    # Train posteriors
    from src.regime.hmm import infer_regime_history
    df_train_hmm = infer_regime_history(hmm_model, state_to_regime, close_train, window=21, ema_span=1)
    
    # Test posteriors
    df_test_hmm = pd.DataFrame(test_posteriors, index=test_idx)
    df_test_hmm = df_test_hmm.rename(columns={"BULL": "p_bull", "BEAR": "p_bear", "SIDEWAYS": "p_sideways"})
    
    for col in ["p_bull", "p_bear"]:
        feature_matrix_fold[col] = 0.0
        if not df_train_hmm.empty and col in df_train_hmm.columns:
            train_vals = df_train_hmm[col].reindex(train_idx)
            feature_matrix_fold.loc[train_idx, col] = train_vals.fillna(0.0)
        if not df_test_hmm.empty and col in df_test_hmm.columns:
            test_vals = df_test_hmm[col].reindex(test_idx)
            feature_matrix_fold.loc[test_idx, col] = test_vals.fillna(0.0)

    # 4. Fit FeatureProcessor on train_idx, transform both train_idx and test_idx
    from src.features.processor import FeatureProcessor
    processor = FeatureProcessor()
    
    # Purge the last train bar where shift(-1) target references the test period
    effective_train_idx = train_idx[:-1] if len(train_idx) > 0 else train_idx

    valid_train_idx = effective_train_idx[~y.loc[effective_train_idx].isna()]
    X_train = feature_matrix_fold.loc[valid_train_idx]
    y_train = y.loc[valid_train_idx]
    X_test = feature_matrix_fold.loc[test_idx]
    
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
    elif ensemble_mode == "xgboost":
        from src.ensemble.xgboost_model import XGBoostEnsemble
        model = XGBoostEnsemble()
        model.fit(X_train_proc, y_train)
        test_scores = model.predict(X_test_proc)
    else:
        from src.ensemble.model import MLConsensusEngine
        model = MLConsensusEngine()
        model.fit(X_train_proc, y_train)
        test_scores = model.predict(X_test_proc)
    
    # 6. Run simulated daily execution pipeline (MockExecutionAdapter)
    adapter = MockExecutionAdapter()
    fold_records = []
    
    # Use annualized returns/volatility from raw data for transitioning telemetry
    log_returns_series = np.log(df_merged["close"] / df_merged["close"].shift(1)).fillna(0.0)
    realized_vol_series = log_returns_series.rolling(21).std().fillna(0.0)
    
    from src.execution.sizing import MA_PERIOD, USE_MA_FILTER
    ma_series = df_merged["close"].rolling(MA_PERIOD).mean() if USE_MA_FILTER else None
    
    # Pre-calculate gates on df_merged
    from src.signals.entropy import ShannonEntropyFilter
    entropy_filter = ShannonEntropyFilter()
    entropy_series = entropy_filter.compute(df_merged)
    
    from src.signals.efficiency_ratio import KaufmanEfficiencyRatioFilter
    er_filter = KaufmanEfficiencyRatioFilter()
    er_series = er_filter.compute(df_merged)
    
    high_m = df_merged["high"]
    low_m = df_merged["low"]
    tenkan_m = (high_m.rolling(20).max() + low_m.rolling(20).min()) / 2
    kijun_m = (high_m.rolling(60).max() + low_m.rolling(60).min()) / 2
    sa_m = ((tenkan_m + kijun_m) / 2).shift(60)
    sb_m = ((high_m.rolling(120).max() + low_m.rolling(120).min()) / 2).shift(60)
    cloud_min_series = np.minimum(sa_m, sb_m)
    
    for i, date in enumerate(test_idx):
        date_str = date.strftime("%Y-%m-%d")
        score = float(test_scores.loc[date])
        
        # Use the cross-day smoothed overridden posteriors and regimes
        overridden_posteriors = test_posteriors_smoothed[i]
        final_regime = test_regimes[i]
        
        onchain_metrics = {}
        for col in ["sth_mvrv", "sth_nupl"]:
            if col in df_merged.columns:
                val = df_merged.loc[date, col]
                onchain_metrics[col] = float(val) if not pd.isna(val) else 0.0
            else:
                onchain_metrics[col] = 0.0
                
        # Score is already in [-1.0, 1.0] from predict_score

        # Removed score inversion (fixes Hit-Rate Inversion Paradox)
        # Ensure score is strictly within [-1.0, 1.0]
        score = max(-1.0, min(1.0, score))
                
        log_ret = float(log_returns_series.loc[date])
        realized_vol = float(realized_vol_series.loc[date])
        
        comp_val = float(df_merged.loc[date, "composite_value"]) if "composite_value" in df_merged.columns else 0.0

        price = float(df_merged.loc[date, "close"])
        ma_val = float(ma_series.loc[date]) if (USE_MA_FILTER and not pd.isna(ma_series.loc[date])) else None

        entropy_val = float(entropy_series.loc[date]) if not pd.isna(entropy_series.loc[date]) else None
        er_val = float(er_series.loc[date]) if not pd.isna(er_series.loc[date]) else None
        cloud_min = float(cloud_min_series.loc[date]) if not pd.isna(cloud_min_series.loc[date]) else None

        res_record = adapter.run(
            date_str=date_str,
            final_score=score,
            regime=final_regime,
            posteriors=overridden_posteriors,
            onchain_metrics=onchain_metrics,
            log_return=log_ret,
            realized_volatility=realized_vol,
            composite_value=comp_val,
            price=price,
            ma_val=ma_val,
            entropy_val=entropy_val,
            er_val=er_val,
            cloud_min=cloud_min
        )
        
        # Extract features for telemetry
        indicator_scores = feature_matrix.loc[date, processor.tech_indicators_list].to_dict()
        indicator_scores = {k: float(v) if not pd.isna(v) else 0.0 for k, v in indicator_scores.items()}
        if "Entropy" in feature_matrix.columns:
            indicator_scores["Entropy"] = float(feature_matrix.loc[date, "Entropy"]) if not pd.isna(feature_matrix.loc[date, "Entropy"]) else 0.0
        if "ER" in feature_matrix.columns:
            indicator_scores["ER"] = float(feature_matrix.loc[date, "ER"]) if not pd.isna(feature_matrix.loc[date, "ER"]) else 0.0
        
        pca_cols = [c for c in X_test_proc.columns if c.startswith("PC")]
        pca_components = X_test_proc.loc[date, pca_cols].to_dict()
        pca_components = {k: float(v) for k, v in pca_components.items()}
        
        if processor.pca is not None:
            pca_components["pca_variance_explained"] = float(np.sum(processor.pca.pca.explained_variance_ratio_)) * 100.0
        else:
            pca_components["pca_variance_explained"] = 100.0
            
        res_record["date"] = date
        res_record["close"] = float(df_merged.loc[date, "close"])
        res_record["indicator_scores"] = indicator_scores
        res_record["pca_components"] = pca_components
        res_record["posteriors"] = overridden_posteriors
        
        fold_records.append(res_record)
        
    return fold_records


class BacktestRunner:
    def __init__(self, legacy_fixed_window: bool = False, ensemble_mode: str = "xgboost"):
        self.legacy_fixed_window = legacy_fixed_window
        self.ensemble_mode = ensemble_mode

    def run(self, data: pd.DataFrame) -> dict:
        """
        Runs the full walk-forward backtest optimization.
        """
        # 1. Calibrate OU half-life (dynamic lookback) on log price levels per spec
        wfo_ens = WFOEnsemble()
        log_prices = np.log(data["close"])
        
        dynamic_lookback = wfo_ens.run_wfo_calibration(
            log_prices,
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
        
        # Define continuous target y computed dynamically via forward returns (no CSV dependencies)
        from src.data.target_loader import load_regime_targets
        y = load_regime_targets(df_merged.index, close_series=df_merged["close"])
        y = y.loc[common_idx]
        
        # 3. Generate WFO folds (3yr train -> 6mo val -> 6mo test)
        iterator = WFOIterator(purge_days=14)
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
        results_df.to_csv('tmp_backtest_results.csv')

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
            "raw_records": records,
            "metrics": {
                "total_return": total_return,
                "annualized_sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "regime_metrics": regime_metrics
            }
        }


def main():
    parser = argparse.ArgumentParser(description="LTTD WFO Backtest Runner")
    parser.add_argument("--ensemble-mode", choices=["pca_consensus", "lasso", "xgboost"], default="xgboost",
                        help="Choose ensemble aggregation mode: 'pca_consensus' (Option A), 'lasso' (Option B), or 'xgboost' (Default)")
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
    
    print("Loading historical on-chain metrics from BRK API...")
    feed = OnChainFeed()
    onchain = feed.fetch_historical_bulk(start=-4500)
    
    print(f"Joining datasets causally...")
    df_merged = point_in_time_join(df_ohlcv, onchain)
    
    print(f"Available data rows for backtest warmup and training: {len(df_merged)}")
    
    runner = BacktestRunner(legacy_fixed_window=args.legacy_fixed_window, ensemble_mode=args.ensemble_mode)
    res = runner.run(df_merged)
    
    # Filter results by date range AFTER out-of-sample predictions are generated
    results_df = res["results"].loc[args.start:args.end]
    res["results"] = results_df
    
    # Re-calculate metrics based on the sliced results
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
    
    bh_return = (close_series.iloc[-1] / close_series.iloc[0]) - 1.0
    # Calculate Buy and Hold portfolio
    bh_portfolio = vbt.Portfolio.from_holding(close_series, init_cash=10000.0, fees=0.001)
    
    metrics = {
        "total_return": portfolio.total_return(),
        "annualized_sharpe": (portfolio.returns().mean() / portfolio.returns().std() * np.sqrt(365)) if portfolio.returns().std() > 0 else 0.0,
        "annualized_sortino": (portfolio.returns().mean() / portfolio.returns()[portfolio.returns() < 0].std() * np.sqrt(365)) if portfolio.returns()[portfolio.returns() < 0].std() > 0 else 0.0,
        "max_drawdown": portfolio.max_drawdown(),
        "bh_return": bh_portfolio.total_return(),
        "bh_sharpe": (bh_portfolio.returns().mean() / bh_portfolio.returns().std() * np.sqrt(365)) if bh_portfolio.returns().std() > 0 else 0.0,
        "bh_max_dd": bh_portfolio.max_drawdown(),
        "regime_metrics": {}
    }
    daily_returns = portfolio.returns()
    for regime_name in ["BULL", "BEAR", "SIDEWAYS"]:
        regime_df = results_df[results_df["regime"] == regime_name]
        if len(regime_df) > 0:
            active_days = daily_returns.loc[regime_df.index.intersection(daily_returns.index)]
            non_zero_days = active_days[results_df.loc[active_days.index, "target_exposure"] > 0]
            hit_rate = float((non_zero_days > 0).sum() / len(non_zero_days)) if len(non_zero_days) > 0 else 0.0
            metrics["regime_metrics"][regime_name] = {"count": len(regime_df), "active_days": len(non_zero_days), "hit_rate": hit_rate}
        else:
            metrics["regime_metrics"][regime_name] = {"count": 0, "active_days": 0, "hit_rate": 0.0}
    
    print("\n==========================================================================")
    print("                      LTTD SYSTEM - BACKTEST RESULTS                      ")
    print("==========================================================================")
    print(f"Total Return             : {metrics['total_return']*100:.2f}% (B&H: {metrics['bh_return']*100:.2f}%)")
    print(f"Annualized Sharpe Ratio  : {metrics['annualized_sharpe']:.4f} (B&H: {metrics['bh_sharpe']:.4f})")
    print(f"Annualized Sortino Ratio : {metrics['annualized_sortino']:.4f}")
    print(f"Max Drawdown             : {metrics['max_drawdown']*100:.2f}% (B&H: {metrics['bh_max_dd']*100:.2f}%)")
    print("\nRegime Partitioned Metrics:")
    for regime, r_met in metrics["regime_metrics"].items():
        print(f"  → {regime:10}: Total Days={r_met['count']:<5} Active Days={r_met['active_days']:<5} Hit Rate={r_met['hit_rate']:.2%}")
    print("==========================================================================")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
