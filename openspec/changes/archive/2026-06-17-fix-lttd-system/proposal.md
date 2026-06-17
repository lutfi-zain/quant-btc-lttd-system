## Why

The LTTD system is **non-functional in production** and produces **statistically meaningless results** in backtesting. An exhaustive architecture audit (by lz-quant-researcher + lz-data-science-core) identified **4 BLOCKERs** and **7 CRITICAL issues** that collectively render the system incapable of generating actionable signals:

1. **Production exposure is ALWAYS ZERO** — a regime name mismatch between HMM (`BULL`/`BEAR`/`SIDEWAYS`) and sizing (`Strong Bull`/`Weak Bull`/etc.) means the system never takes a position. Every live run silently does nothing. [P0 BLOCKER]

2. **The signal is contrarian** — IC is negative at ALL horizons (-0.045 at 1d, -0.203 at 21d). When the model predicts bullish, BTC goes down. The system has predictive power — in the wrong direction. [P0 BLOCKER]

3. **The model trains on fake data** — 51 hand-labeled ISP regime transitions are forward-filled to create 2,483 daily samples. Only 37 labels fall within the database range. Effective N ≈ 37, far below XGBoost's requirements. [P1 BLOCKER]

4. **On-chain features are never fed to the ML model** — 4 high-quality metrics (STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit) are fetched from BRK API but only used for binary threshold overrides. They never enter the feature matrix. [P1 BLOCKER]

**The gap analysis confirms**: even after fixing all issues, the LTTD system will achieve 50-70% CAGR (vs ISP reference's 130.6%). But the current system achieves 0% — it literally does nothing. This change moves the system from "non-functional" to "marginally viable."

## What Changes

### P0 Fixes (Must-fix production bugs)

- **Fix regime name mapping**: Add `{"BULL": "Weak Bull", "BEAR": "Weak Bear", "SIDEWAYS": "Neutral"}` mapping in `pipeline.py` before execution engine. This enables actual trading. [5-line fix]

- **Invert the signal**: Multiply `final_score` by -1 to convert contrarian IC (-0.203) to momentum IC (+0.203). This immediately converts the signal direction. [1-line fix]

### P1 Fixes (Must-fix for model to learn)

- **Replace forward-fill target with forward return prediction**: Predict 21-day forward log return, z-score normalize, clip to [-1, +1]. This eliminates 2,432 fake training samples. [Medium effort]

- **Add on-chain features to feature matrix**: Append STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit as columns in `FeatureMatrixBuilder.build_matrix()`. [Low effort]

- **Drop redundant indicators**: Remove QuantileDEMA (VIF → ∞ with FDI). Remove KalmanRSI (400-day lag). Keep TrendStrengthIndex, FourierSupertrend, AdvancedStochastic, FDI. [Low effort]

- **Fix XGBoost objective**: Change `objective="reg:logistic"` to `objective="reg:squarederror"` for continuous targets. Or replace XGBoost entirely with PCAConsensusEnsemble. [Low effort]

### P2 Fixes (Should-fix for performance)

- **Reduce signal lag**: Remove Kalman filter from KalmanRSI. Reduce AdvancedStochastic loop from 1-129 to 1-30 periods. Reduce RollingNormalizer window from 800 to 200. Target: ACF(1) < 0.85. [Medium effort]

- **Add HMM posteriors as features**: Include `p_bull`, `p_bear`, `p_sideways` in the feature matrix. [Low effort]

- **Continuous sizing**: Replace binary in/out with conviction-weighted sizing based on `final_score` and realized volatility. [Medium effort]

### P3 Fixes (Nice-to-have)

- **Backtest-production alignment**: Unify purge days (14 in backtest, 7 in production → use 14 everywhere). Unify regime mapping (backtest uses score→5-level, production uses HMM→3-level → use score→5-level everywhere). [Low effort]

## Capabilities

### New Capabilities

- `target-variable-redesign`: Replace forward-filled ISP labels with forward return prediction as the ML training target. This fixes the fundamental data quality issue that causes the model to train on fake samples.

- `onchain-feature-integration`: Add on-chain metrics (STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit) to the ML feature matrix. Currently fetched but unused in ensemble training.

- `signal-lag-reduction`: Reduce indicator lag by removing Kalman filter, shortening stochastic periods, and reducing normalization windows. Target: ACF(1) < 0.85 (from 0.96).

- `conviction-weighted-sizing`: Replace binary in/out position sizing with continuous sizing based on final_score and realized volatility.

### Modified Capabilities

- `pipeline-orchestrator`: Add regime name mapping (HMM → 5-level) before execution engine. Fix signal inversion.

- `ensemble-aggregation`: Replace XGBoost with PCAConsensusEnsemble as default. Fix objective function if keeping XGBoost.

- `indicator-signals`: Remove QuantileDEMA (VIF → ∞) and KalmanRSI (400-day lag). Reduce AdvancedStochastic periods.

## Impact

### Code Changes

| File | Change | Effort |
|------|--------|--------|
| `src/pipeline.py` | Add regime mapping + signal inversion | 1 hour |
| `src/data/target_loader.py` | Replace forward-fill with forward returns | 2 days |
| `src/features/builder.py` | Add on-chain columns to feature matrix | 2 hours |
| `src/ensemble/xgboost_model.py` | Fix objective or replace with PCAConsensus | 2 hours |
| `src/signals/kalman_rsi.py` | Remove Kalman filter, reduce RSI period | 4 hours |
| `src/signals/advanced_stochastic.py` | Reduce loop from 1-129 to 1-30 | 2 hours |
| `src/signals/quantile_dema.py` | Remove from feature matrix | 30 min |
| `src/execution/sizing.py` | Add conviction-weighted sizing | 1 day |
| `src/backtest/runner.py` | Align purge days and regime mapping | 2 hours |

### Dependencies

- No new external dependencies required
- On-chain data already fetched via `brk-client` — just needs to be added to feature matrix

### Risk Assessment

| Risk | Mitigation |
|------|------------|
| Signal inversion may not work if IC is negative due to target bias | Fix target variable FIRST, then re-evaluate IC direction |
| Forward return target may reduce interpretability | Keep regime labels for presentation, use forward returns only for ML training |
| Reducing indicator lag may increase false signals | Test ACF(1) < 0.85 target before deploying |

### Backtest Impact (Estimated)

| Metric | Current | After P0 Fix | After P1 Fix | After P2 Fix |
|--------|---------|--------------|--------------|--------------|
| IC (21d) | -0.203 | +0.203 | +0.05 to +0.10 | +0.10 to +0.15 |
| Sharpe | N/A | 0.5-0.8 | 1.0-1.5 | 1.2-1.8 |
| Max DD | N/A | -30-40% | -20-30% | -15-25% |
| ACF(1) | 0.96 | 0.96 | 0.90-0.93 | 0.85-0.90 |
| CAGR | 0% | 20-40% | 50-70% | 60-80% |

**Note**: These are estimated improvements. Actual results depend on market conditions and implementation quality. The ISP reference (130.6% CAGR, -6.8% DD) represents a ceiling that ML systems cannot match.
