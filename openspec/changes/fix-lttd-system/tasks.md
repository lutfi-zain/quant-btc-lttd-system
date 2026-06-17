## 1. P0 Fixes — Production Functionality (1 day)

- [x] 1.1 Fix regime name mapping in `src/pipeline.py`: Add `{"BULL": "Weak Bull", "BEAR": "Weak Bear", "SIDEWAYS": "Neutral"}` mapping before execution engine
- [x] 1.2 Add signal inversion in `src/pipeline.py`: Multiply `final_score` by -1 after ensemble computation
- [x] 1.3 Verify production exposure > 0: Run pipeline and check `target_exposure` is not always 0.0
- [x] 1.4 Run tests: `python -m pytest -xvs` — all existing tests must pass
- [x] 1.5 Commit: `fix(execution): map HMM regime to 5-level and invert signal`

## 2. P1 Fixes — Target Variable Redesign (2-3 days)

- [x] 2.1 Create new target loader in `src/data/target_loader.py`: Compute 21-day forward log return
- [x] 2.2 Add z-score normalization: Rolling 252-day window, clip to [-1, +1]
- [x] 2.3 Update `src/pipeline.py` to use new target loader instead of ISP labels
- [x] 2.4 Remove forward-fill logic from `target_loader.py`
- [x] 2.5 Add target freshness validation: Ensure target for date `t` uses only data up to `t+21`
- [x] 2.6 Write unit tests for target variable computation
- [x] 2.7 Run tests: `python -m pytest -xvs`
- [x] 2.8 Commit: `feat(target): replace forward-filled ISP labels with forward returns`

## 3. P1 Fixes — On-Chain Feature Integration (1 day)

- [x] 3.1 Modify `src/features/builder.py`: Add `onchain_df` parameter to `build_matrix()`
- [x] 3.2 Add on-chain columns (sth_mvrv, sth_nupl, sth_sopr_24h, sth_supply_in_profit) to feature matrix
- [x] 3.3 Update `src/pipeline.py` to pass on-chain data to `build_matrix()`
- [x] 3.4 Verify on-chain features appear in VIF analysis output
- [x] 3.5 Run tests: `python -m pytest -xvs`
- [x] 3.6 Commit: `feat(features): add on-chain metrics to ML feature matrix`

## 4. P1 Fixes — Indicator Suite Reduction (1 day)

- [x] 4.1 Remove QuantileDEMA from feature matrix in `src/features/builder.py`
- [x] 4.2 Remove KalmanRSI from feature matrix in `src/features/builder.py`
- [x] 4.3 Add RSI-50 variant to signal engine (RSI period=50, no Kalman filter)
- [x] 4.4 Verify VIF analysis shows no indicator with VIF → ∞
- [x] 4.5 Run tests: `python -m pytest -xvs`
- [x] 4.6 Commit: `feat(signals): remove QuantileDEMA and KalmanRSI, add RSI-50`

## 5. P1 Fixes — Ensemble Model Replacement (1 day)

- [x] 5.1 Set `PCAConsensusEnsemble` as default in `src/pipeline.py`
- [x] 5.2 Add StandardScaler to `PCAConsensusEnsemble` for raw feature input
- [x] 5.3 Fix XGBoost objective in `src/ensemble/xgboost_model.py`: Change to `reg:squarederror`
- [x] 5.4 Reduce XGBoost `n_estimators` from 300 to 50
- [x] 5.5 Add HMM posteriors (p_bull, p_bear, p_sideways) to feature matrix
- [x] 5.6 Run tests: `python -m pytest -xvs`
- [x] 5.7 Commit: `feat(ensemble): replace XGBoost with PCAConsensusEnsemble as default`

## 6. P2 Fixes — Signal Lag Reduction (2-3 days)

- [x] 6.1 Modify `src/signals/kalman_rsi.py`: Remove Kalman filter, reduce RSI period to 50
- [x] 6.2 Modify `src/signals/advanced_stochastic.py`: Reduce loop from 1-129 to 1-30
- [x] 6.3 Modify `src/features/normalizer.py`: Reduce RollingNormalizer max window from 800 to 200
- [x] 6.4 Measure ACF(1) of final_score after changes
- [x] 6.5 Verify ACF(1) < 0.85 (target: half-life ≈ 4 days)
- [x] 6.6 Run tests: `python -m pytest -xvs`
- [x] 6.7 Commit: `feat(signals): reduce indicator lag, target ACF(1) < 0.85`

## 7. P2 Fixes — Conviction-Weighted Sizing (1 day)

- [x] 7.1 Modify `src/execution/sizing.py`: Implement conviction-weighted formula
- [x] 7.2 Add EMA smoothing (span=5) to exposure calculation
- [x] 7.3 Add exposure bounds (min=0.3, max=1.0)
- [x] 7.4 Add volatility scalar: `vol_scalar = max(0.3, 1.0 - vol / 0.8)`
- [x] 7.5 Update `src/pipeline.py` to pass volatility to sizing function
- [x] 7.6 Run tests: `python -m pytest -xvs`
- [x] 7.7 Commit: `feat(execution): implement conviction-weighted position sizing`

## 8. P3 Fixes — Backtest-Production Alignment (1 day)

- [x] 8.1 Update `src/pipeline.py`: Change purge_days from 7 to 14
- [x] 8.2 Verify backtest runner and pipeline use identical purge days
- [x] 8.3 Update `src/backtest/runner.py`: Use score-based regime mapping (same as pipeline)
- [x] 8.4 Run full backtest with WFO
- [x] 8.5 Compare before/after metrics (IC, ACF(1), Sharpe, max drawdown)
- [x] 8.6 Commit: `fix(backtest): align purge days and regime mapping with pipeline`

## 9. Validation & Documentation (1 day)

- [ ] 9.1 Run full test suite: `python -m pytest --cov`
- [ ] 9.2 Generate backtest performance report
- [ ] 9.3 Update AGENTS.md with new ensemble defaults and sizing formula
- [ ] 9.4 Create migration guide for existing deployments
- [ ] 9.5 Commit: `docs: update documentation for system fixes`
