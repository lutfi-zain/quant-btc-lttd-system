## 1. P0 Fixes — Production Functionality (1 day)

- [ ] 1.1 Fix regime name mapping in `src/pipeline.py`: Add `{"BULL": "Weak Bull", "BEAR": "Weak Bear", "SIDEWAYS": "Neutral"}` mapping before execution engine
- [ ] 1.2 Add signal inversion in `src/pipeline.py`: Multiply `final_score` by -1 after ensemble computation
- [ ] 1.3 Verify production exposure > 0: Run pipeline and check `target_exposure` is not always 0.0
- [ ] 1.4 Run tests: `python -m pytest -xvs` — all existing tests must pass
- [ ] 1.5 Commit: `fix(execution): map HMM regime to 5-level and invert signal`

## 2. P1 Fixes — Target Variable Redesign (2-3 days)

- [ ] 2.1 Create new target loader in `src/data/target_loader.py`: Compute 21-day forward log return
- [ ] 2.2 Add z-score normalization: Rolling 252-day window, clip to [-1, +1]
- [ ] 2.3 Update `src/pipeline.py` to use new target loader instead of ISP labels
- [ ] 2.4 Remove forward-fill logic from `target_loader.py`
- [ ] 2.5 Add target freshness validation: Ensure target for date `t` uses only data up to `t+21`
- [ ] 2.6 Write unit tests for target variable computation
- [ ] 2.7 Run tests: `python -m pytest -xvs`
- [ ] 2.8 Commit: `feat(target): replace forward-filled ISP labels with forward returns`

## 3. P1 Fixes — On-Chain Feature Integration (1 day)

- [ ] 3.1 Modify `src/features/builder.py`: Add `onchain_df` parameter to `build_matrix()`
- [ ] 3.2 Add on-chain columns (sth_mvrv, sth_nupl, sth_sopr_24h, sth_supply_in_profit) to feature matrix
- [ ] 3.3 Update `src/pipeline.py` to pass on-chain data to `build_matrix()`
- [ ] 3.4 Verify on-chain features appear in VIF analysis output
- [ ] 3.5 Run tests: `python -m pytest -xvs`
- [ ] 3.6 Commit: `feat(features): add on-chain metrics to ML feature matrix`

## 4. P1 Fixes — Indicator Suite Reduction (1 day)

- [ ] 4.1 Remove QuantileDEMA from feature matrix in `src/features/builder.py`
- [ ] 4.2 Remove KalmanRSI from feature matrix in `src/features/builder.py`
- [ ] 4.3 Add RSI-50 variant to signal engine (RSI period=50, no Kalman filter)
- [ ] 4.4 Verify VIF analysis shows no indicator with VIF → ∞
- [ ] 4.5 Run tests: `python -m pytest -xvs`
- [ ] 4.6 Commit: `feat(signals): remove QuantileDEMA and KalmanRSI, add RSI-50`

## 5. P1 Fixes — Ensemble Model Replacement (1 day)

- [ ] 5.1 Set `PCAConsensusEnsemble` as default in `src/pipeline.py`
- [ ] 5.2 Add StandardScaler to `PCAConsensusEnsemble` for raw feature input
- [ ] 5.3 Fix XGBoost objective in `src/ensemble/xgboost_model.py`: Change to `reg:squarederror`
- [ ] 5.4 Reduce XGBoost `n_estimators` from 300 to 50
- [ ] 5.5 Add HMM posteriors (p_bull, p_bear, p_sideways) to feature matrix
- [ ] 5.6 Run tests: `python -m pytest -xvs`
- [ ] 5.7 Commit: `feat(ensemble): replace XGBoost with PCAConsensusEnsemble as default`

## 6. P2 Fixes — Signal Lag Reduction (2-3 days)

- [ ] 6.1 Modify `src/signals/kalman_rsi.py`: Remove Kalman filter, reduce RSI period to 50
- [ ] 6.2 Modify `src/signals/advanced_stochastic.py`: Reduce loop from 1-129 to 1-30
- [ ] 6.3 Modify `src/features/normalizer.py`: Reduce RollingNormalizer max window from 800 to 200
- [ ] 6.4 Measure ACF(1) of final_score after changes
- [ ] 6.5 Verify ACF(1) < 0.85 (target: half-life ≈ 4 days)
- [ ] 6.6 Run tests: `python -m pytest -xvs`
- [ ] 6.7 Commit: `feat(signals): reduce indicator lag, target ACF(1) < 0.85`

## 7. P2 Fixes — Conviction-Weighted Sizing (1 day)

- [ ] 7.1 Modify `src/execution/sizing.py`: Implement conviction-weighted formula
- [ ] 7.2 Add EMA smoothing (span=5) to exposure calculation
- [ ] 7.3 Add exposure bounds (min=0.3, max=1.0)
- [ ] 7.4 Add volatility scalar: `vol_scalar = max(0.3, 1.0 - vol / 0.8)`
- [ ] 7.5 Update `src/pipeline.py` to pass volatility to sizing function
- [ ] 7.6 Run tests: `python -m pytest -xvs`
- [ ] 7.7 Commit: `feat(execution): implement conviction-weighted position sizing`

## 8. P3 Fixes — Backtest-Production Alignment (1 day)

- [ ] 8.1 Update `src/pipeline.py`: Change purge_days from 7 to 14
- [ ] 8.2 Verify backtest runner and pipeline use identical purge days
- [ ] 8.3 Update `src/backtest/runner.py`: Use score-based regime mapping (same as pipeline)
- [ ] 8.4 Run full backtest with WFO
- [ ] 8.5 Compare before/after metrics (IC, ACF(1), Sharpe, max drawdown)
- [ ] 8.6 Commit: `fix(backtest): align purge days and regime mapping with pipeline`

## 9. Validation & Documentation (1 day)

- [ ] 9.1 Run full test suite: `python -m pytest --cov`
- [ ] 9.2 Generate backtest performance report
- [ ] 9.3 Update AGENTS.md with new ensemble defaults and sizing formula
- [ ] 9.4 Create migration guide for existing deployments
- [ ] 9.5 Commit: `docs: update documentation for system fixes`
