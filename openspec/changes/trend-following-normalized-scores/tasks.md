## 1. TrendComponent Base Class

- [ ] 1.1 Create `src/signals/trend_component.py` with abstract `TrendComponent` class
- [ ] 1.2 Implement `compute()` abstract method returning pd.Series ∈ [0, 1]
- [ ] 1.3 Implement configurable `buy_threshold` and `sell_threshold` parameters (defaults: 0.6, 0.4)
- [ ] 1.4 Implement `signal()` method converting confidence scores to directional signals {-1.0, 0.0, +1.0}
- [ ] 1.5 Implement `_adjust_thresholds()` method for regime-aware threshold modification
- [ ] 1.6 Add `regime_adjusted` parameter to bypass threshold adjustment when False
- [ ] 1.7 Write unit tests for TrendComponent interface (test_score_range, test_signal_generation, test_threshold_adjustment)

## 2. Five-State Regime Detection

- [ ] 2.1 Add `classify_5state()` function to `src/regime/hmm.py` using posterior thresholds
- [ ] 2.2 Implement threshold logic: Strong Bull (P_bull > 0.7), Weak Bull (P_bull > 0.4), Neutral (no P > 0.4), Weak Bear (P_bear > 0.4), Strong Bear (P_bear > 0.7)
- [ ] 2.3 Add confidence score calculation (max posterior probability)
- [ ] 2.4 Add regime transition logging with timestamp, from/to regimes, posteriors
- [ ] 2.5 Update `infer_regime()` to return 5-state classification instead of 3-state
- [ ] 2.6 Update `infer_regime_history()` to return 5-state regime history
- [ ] 2.7 Write unit tests for 5-state classification (test_strong_bull, test_weak_bull, test_neutral, test_weak_bear, test_strong_bear)
- [ ] 2.8 Validate 5-state classification against ISP regimes CSV (target: ≥70% accuracy)

## 3. Coherence Engine

- [ ] 3.1 Create `src/ensemble/coherence.py` with `CoherenceEngine` class
- [ ] 3.2 Implement `evaluate()` method accepting Dict[str, pd.Series] of component signals
- [ ] 3.3 Implement majority voting mode (≥50%+1 agreement required)
- [ ] 3.4 Implement supermajority voting mode (≥75%+1 agreement required)
- [ ] 3.5 Implement unanimous voting mode (100% agreement required)
- [ ] 3.6 Implement configurable `min_agreement` parameter to override mode
- [ ] 3.7 Return voting statistics: buy_votes, sell_votes, total_components, coherence_signal, confidence
- [ ] 3.8 Write unit tests for coherence voting (test_majority_buy, test_majority_sell, test_no_majority, test_supermajority, test_unanimous)

## 4. Regime-Aware Thresholds

- [ ] 4.1 Create `src/ensemble/regime_thresholds.py` with adjustment matrix
- [ ] 4.2 Implement threshold adjustments: Strong Bull (-0.1, +0.1), Weak Bull (0.0, 0.0), Neutral (+0.1, -0.1), Weak Bear (+0.2, -0.2), Strong Bear (+0.3, -0.3)
- [ ] 4.3 Implement threshold clamping to [0.1, 0.9] range
- [ ] 4.4 Integrate threshold adjustments into TrendComponent.signal() method
- [ ] 4.5 Write unit tests for threshold adjustments (test_all_regimes, test_clamping, test_bypass)

## 5. Component Migration (6 Indicators)

- [ ] 5.1 Create `src/signals/momentum_score.py` — new TrendComponent for price momentum
- [ ] 5.2 Create `src/signals/onchain_score.py` — new TrendComponent combining MVRV, SOPR, NUPL
- [ ] 5.3 Migrate `src/signals/kalman_rsi.py` to TrendComponent interface (wrap existing)
- [ ] 5.4 Migrate `src/signals/fdi.py` to TrendComponent interface (wrap existing)
- [ ] 5.5 Migrate `src/signals/quantile_dema.py` to TrendComponent interface (wrap existing)
- [ ] 5.6 Migrate `src/signals/fourier_supertrend.py` to TrendComponent interface (wrap existing)
- [ ] 5.7 Migrate `src/signals/advanced_stochastic.py` to TrendComponent interface (wrap existing)
- [ ] 5.8 Migrate `src/signals/trend_strength.py` to TrendComponent interface (wrap existing)
- [ ] 5.9 Write unit tests for each migrated component (verify [0, 1] output, causality)

## 6. Execution Engine Rewrite

- [ ] 6.1 Create `src/execution/sizing_5state.py` with new position sizing logic
- [ ] 6.2 Implement discrete position sizing: {0.0, 0.5, 1.0}
- [ ] 6.3 Implement ISP pattern: Weak Bull + BUY → 50%, Strong Bull + BUY → 100%
- [ ] 6.4 Implement ISP pattern: Weak Bull + SELL → 50%, Neutral + SELL → 0%
- [ ] 6.5 Implement Bear regime override: Weak Bear/Strong Bear → 0% regardless of signal
- [ ] 6.6 Integrate coherence signal with regime for final trade decision
- [ ] 6.7 Write unit tests for 5-state sizing (test_weak_bull_buy, test_strong_bull_buy, test_weak_bull_sell, test_neutral_sell, test_bear_override)

## 7. Pipeline Integration

- [ ] 7.1 Update `src/pipeline.py` to use new TrendComponent interface
- [ ] 7.2 Replace PCA/Lasso aggregation with CoherenceEngine in pipeline
- [ ] 7.3 Replace 3-state sizing with 5-state sizing in pipeline
- [ ] 7.4 Update pipeline to pass regime to CoherenceEngine and threshold adjustments
- [ ] 7.5 Write integration test for full pipeline (data → regime → components → coherence → sizing)

## 8. ISP Validation

- [ ] 8.1 Create `src/backtest/isp_validator.py` with validation functions
- [ ] 8.2 Implement `validate_against_isp()` comparing backtest vs ISP signals CSV
- [ ] 8.3 Calculate signal timing alignment (target: ≥80%)
- [ ] 8.4 Calculate regime alignment (target: ≥70%)
- [ ] 8.5 Calculate position sizing MSE (target: <0.01)
- [ ] 8.6 Calculate equity curve correlation (target: ≥0.90)
- [ ] 8.7 Run full backtest against ISP data (2015-2025) and generate validation report
- [ ] 8.8 Document any alignment gaps and tuning recommendations

## 9. WFO Updates

- [ ] 9.1 Update `src/backtest/wfo.py` to use regime transition as target variable
- [ ] 9.2 Add component threshold optimization to WFO pipeline
- [ ] 9.3 Update WFO objective to maximize ISP signal alignment (not just R²)
- [ ] 9.4 Write unit tests for WFO with new target variable

## 10. Documentation & Cleanup

- [ ] 10.1 Update `AGENTS.md` with new architecture (5-state regime, [0, 1] scores, coherence)
- [ ] 10.2 Update domain language definitions (Component Score ∈ [0, 1], Coherence Signal)
- [ ] 10.3 Deprecate old PCA/Lasso ensemble code (keep for reference)
- [ ] 10.4 Update pipeline.py docstrings to reflect new layer structure
