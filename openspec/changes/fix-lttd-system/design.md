## Context

The LTTD system is a 6-layer quantitative trading pipeline for Bitcoin long-term trend direction classification. An exhaustive architecture audit identified 4 BLOCKERs and 7 CRITICAL issues that render the system non-functional:

**Current state:**

- Production: exposure = 0 always (regime name mismatch)
- Backtest: negative IC (-0.203), ACF(1)=0.96, effective N=37
- ML model: XGBoost with wrong objective, overfitting catastrophically
- Features: 6 technical indicators only, on-chain metrics unused
- Target: forward-filled ISP labels creating 2,432 fake samples from 51 ground truth

**Architecture layers affected:**

- Layer 2 (Signal Engine): Remove redundant indicators, reduce lag
- Layer 3 (Feature Processing): Add on-chain features, fix VIF handling
- Layer 4 (Ensemble): Replace XGBoost, fix target variable
- Layer 5 (Execution): Fix regime mapping, add conviction sizing

## Goals / Non-Goals

**Goals:**

1. Make the system functional in production (exposure > 0)
2. Achieve positive IC (signal in correct direction)
3. Reduce ACF(1) from 0.96 to < 0.85
4. Add on-chain features to ML model
5. Replace forward-filled target with forward returns
6. Achieve estimated Sharpe 1.0-1.5 in backtest

**Non-Goals:**

1. Match ISP reference performance (130.6% CAGR) — this is a ceiling ML cannot reach
2. Implement new indicators beyond existing 6 + 4 on-chain
3. Change the 3-state HMM architecture
4. Add new data sources (already have OHLCV + BRK on-chain)
5. Modify the presentation layer (Layer 6)

## Decisions

### Decision 1: Target Variable — Forward Returns vs ISP Labels

**Choice:** Replace forward-filled ISP labels with 21-day forward log return (z-score normalized, clipped to [-1, +1]).

**Rationale:**

- ISP labels create 2,432 fake samples from 51 ground truth → effective N=37
- Forward returns provide 1 ground truth per day → effective N=2,483
- Forward returns are objective (market data), not subjective (human labels)
- 21-day horizon aligns with ISP average trade interval (128 days / 6 ≈ 21 days)

**Alternatives considered:**

- Keep ISP labels but sample only at transitions → N=37, too small for XGBoost
- Use regime classification (BULL/BEAR/SIDEWAYS) → loses intensity information
- Use 60-day or 90-day returns → too long for signal responsiveness

**Backtest Impact:** Expected IC improvement from -0.203 to +0.05-0.10

### Decision 2: Ensemble Model — PCAConsensusEnsemble vs XGBoost

**Choice:** Replace XGBoost with PCAConsensusEnsemble as default ensemble.

**Rationale:**

- PCAConsensusEnsemble: `score = Σ |pc1_loading_i| × X[col_i]` — no fitting on targets
- XGBoost with 300 trees on N=37 → extreme overfitting
- PCAConsensusEnsemble is "the most mathematically defensible approach" per audit
- Zero hyperparameter tuning required
- Deterministic output (no randomness from subsampling)

**Alternatives considered:**

- Fix XGBoost objective to `reg:squarederror` → still overfits with N=37
- Use L1-Lasso → wasted on PCA components (L1 ≡ L2 on orthogonal features)
- Use Ridge regression → equivalent to Lasso on PCA components
- Keep XGBoost but reduce `n_estimators` to 50 → still overfits with N=37

**Backtest Impact:** Expected reduction in overfitting variance by 50-70%

### Decision 3: Signal Lag Reduction — Aggressive vs Conservative

**Choice:** Aggressive lag reduction targeting ACF(1) < 0.85.

**Changes:**

- Remove Kalman filter from KalmanRSI (Q=0.75, R=205 → 400-day lag)
- Reduce AdvancedStochastic periods from 1-129 to 1-30
- Reduce RollingNormalizer window from 800 to 200 days
- Keep TrendStrengthIndex unchanged (already 70-day lag)

**Rationale:**

- ACF(1)=0.96 means 96% of today's score = yesterday's score
- Half-life = -ln(2)/ln(0.96) ≈ 17 days → signal changes detected 17 days late
- Target ACF(1)=0.85 → half-life ≈ 4 days → much more responsive
- ISP enters/exits within 4-7 days of transitions → we need comparable speed

**Alternatives considered:**

- Conservative: only remove Kalman filter → ACF(1) ≈ 0.90-0.93
- Minimal: reduce RollingNormalizer only → ACF(1) ≈ 0.92-0.95
- Extreme: use raw indicators without smoothing → too noisy

**Backtest Impact:** Expected improvement in IC from 0.05 to 0.10-0.15 (faster detection = better timing)

### Decision 4: On-Chain Feature Integration — Raw vs Processed

**Choice:** Add raw on-chain values to feature matrix, let PCA handle correlation.

**Rationale:**

- On-chain metrics (MVRV, NUPL, SOPR, SupplyInProfit) are already fetched via BRK
- They measure different information than price-based indicators (valuation, sentiment, behavior)
- PCA will orthogonalize them with technical indicators
- VIF analysis will flag any redundancy

**Alternatives considered:**

- Create derived on-chain features (z-scores, momentum) → premature optimization
- Use on-chain only as regime filters (current approach) → wastes information
- Create separate on-chain ensemble → adds complexity without clear benefit

**Backtest Impact:** Expected IC improvement of 0.02-0.05

### Decision 5: Conviction-Weighted Sizing — Kelly vs Fixed

**Choice:** Implement simple conviction-weighted sizing (not full Kelly).

**Formula:**

```python
def calculate_target_exposure(final_score: float, vol: float) -> float:
    conviction = abs(final_score)  # [0, 1]
    base_exposure = 0.5 + 0.5 * conviction  # [0.5, 1.0]
    vol_scalar = max(0.3, 1.0 - vol / 0.8)  # reduce exposure in high vol
    return base_exposure * vol_scalar
```

**Rationale:**

- Current: binary in/out (0.0 or 1.0-1.5x) — no conviction scaling
- ISP: uses 50% → 100% based on conviction
- Kelly is theoretically optimal but requires accurate edge/vol estimates
- Simple conviction weighting is more robust with uncertain estimates

**Alternatives considered:**

- Full Kelly: `f* = edge / vol²` → requires accurate edge estimate (we don't have it)
- Fixed fractional: always 50% → doesn't scale with conviction
- Binary: current approach → ignores conviction entirely

**Backtest Impact:** Expected max drawdown reduction of 5-10%

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Signal inversion doesn't work if IC is negative due to target bias | Medium | High | Fix target variable FIRST, then re-evaluate IC direction |
| Forward returns reduce interpretability | Low | Low | Keep regime labels for presentation, use forward returns only for ML training |
| Reducing lag increases false signals | Medium | Medium | Test ACF(1) < 0.85 target before deploying; can revert to conservative |
| On-chain features add noise | Low | Low | PCA will downweight noisy features; VIF will flag redundancy |
| PCAConsensusEnsemble underperforms XGBoost | Low | Medium | Keep XGBoost as fallback with reduced n_estimators=50 |
| Conviction sizing produces erratic exposure | Low | Medium | Add smoothing (EMA of exposure) and bounds (min=0.3, max=1.0) |

## Migration Plan

### Phase 1: P0 Fixes (1 day)

1. Add regime name mapping in `pipeline.py`
2. Add signal inversion (`final_score *= -1`)
3. Verify production exposure > 0
4. Run tests: `python -m pytest -xvs`

### Phase 2: P1 Fixes (3-5 days)

1. Replace target variable in `target_loader.py`
2. Add on-chain features in `builder.py`
3. Remove QuantileDEMA and KalmanRSI from feature matrix
4. Replace XGBoost with PCAConsensusEnsemble
5. Run backtest: verify IC > 0, ACF(1) < 0.90

### Phase 3: P2 Fixes (2-3 days)

1. Reduce AdvancedStochastic periods
2. Reduce RollingNormalizer window
3. Add HMM posteriors as features
4. Implement conviction-weighted sizing
5. Run backtest: verify ACF(1) < 0.85, Sharpe > 1.0

### Phase 4: P3 Fixes (1 day)

1. Align purge days (use 14 everywhere)
2. Align regime mapping (use score→5-level everywhere)
3. Run full backtest with WFO
4. Compare before/after metrics

### Rollback Strategy

- Each phase is independently deployable
- Git commit after each phase
- If any phase degrades performance, revert that phase only
- Keep previous ensemble model as fallback

## Open Questions

1. **Should we keep XGBoost as a fallback option?** The audit suggests PCAConsensusEnsemble is more robust, but XGBoost might perform better with more data in the future.

2. **What is the optimal forward return horizon?** 21 days is chosen to match ISP trade frequency, but 30 or 60 days might capture more regime-level information.

3. **Should on-chain features use raw values or z-scores?** Raw values might be more interpretable, but z-scores normalize across different scales.

4. **How to handle the transition from old target to new target?** The model trained on ISP labels will have different characteristics than the model trained on forward returns.
