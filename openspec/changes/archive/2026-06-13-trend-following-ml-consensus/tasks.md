## 1. Target Data Preparation

- [x] 1.1 Implement target forward-filling pipeline to convert sparse `isp-regimes-btcusd.csv` into a continuous daily target array (`y_t`).
- [x] 1.2 Add target data validation to ensure there are no gaps or lookahead leakage during the alignment of X and y.

## 2. Signal Normalization (Layer 2 & 3)

- [x] 2.1 Implement `RollingNormalizer` in `src/features/` using causal Empirical CDF or MinMax with an 800+ day window.
- [x] 2.2 Refactor all existing `src/signals/` components to output bounded `[0.0, 1.0]` intensities rather than discrete votes.
- [x] 2.3 Write `test_no_lookahead()` unit tests specifically for the rolling normalization layer.

## 3. ML Consensus Engine (Layer 4)

- [x] 3.1 Implement the L1-regularized `MLConsensusEngine` class to compute the optimal weights (W) for the additive average.
- [x] 3.2 Implement threshold discretization mapping inside the ensemble engine (e.g., >0.8 -> Strong Bull, etc.).
- [x] 3.3 Integrate the `MLConsensusEngine` with the Walk-Forward Optimization (WFO) runner to train strictly out-of-sample.

## 4. Backtesting & Validation

- [x] 4.1 Run full historical backtest and verify that the L1 penalty drops collinear indicators (VIF < 10 implicitly enforced).
- [x] 4.2 Verify that the generated regime state outputs mathematically align with the `isp-regimes-btcusd.csv` targets without forward-peeking.
