## 1. Feature Implementation (Layer 3)

- [x] 1.1 Create `src/features/ou_calibration.py` to handle Ornstein-Uhlenbeck (OU) mean-reversion half-life estimation.
- [x] 1.2 Implement OLS regression on the AR(1) discretized OU process and compute half-life as `HL = -ln(2)/ln(|b|)`.
- [x] 1.3 Add constraints to strictly clamp the estimated half-life within the [120, 350] day bounds.
- [x] 1.4 Implement fallback logic to return the upper bound (350 days) when `b >= 1` or when historical data is insufficient.
- [x] 1.5 Write the `test_no_lookahead` unit test for the OU calibration pipeline to ensure zero lookahead bias.

## 2. Signal Layer Integration (Layer 2)

- [x] 2.1 Refactor `CausalFilter` in `src/signals/base.py` to accept a `dynamic_lookback` parameter/callback.
- [x] 2.2 Implement safe resizing of filter bounds, strictly using historical lags `source[t-k]` without symmetric windows.
- [x] 2.3 Update existing Technical Indicators to accept and utilize the dynamic OU Half-Life context window.
- [x] 2.4 Verify that On-Chain Metric lookbacks (e.g., from BRK Series) are completely unaffected by dynamic resizing and maintain their 800-1,200 day scales.

## 3. Backtest & WFO Integration (Layer 4)

- [x] 3.1 Update the WFO engine in `src/ensemble/wfo.py` to recalculate the baseline OU Half-Life quarterly during train boundaries.
- [x] 3.2 Ensure WFO recalibration strictly uses purged in-sample data and does not introduce out-of-sample data leaks.
- [x] 3.3 Add a `--legacy-fixed-window` parameter to the backtest `Runner` to force a static 200-day window for legacy unit tests.
- [x] 3.4 Verify that the OU Half-Life is not injected as an additive feature matrix column (VIF = 0 for the OU value itself).

## 4. Verification & Validation

- [x] 4.1 Run Variance Inflation Factor (VIF) checks post-adjustment to ensure the dynamic indicators do not exceed the threshold of 10.
- [x] 4.2 If multicollinearity exceeds VIF bounds, apply Pratt's Measure pruning to remove redundant dynamic indicators.
- [x] 4.3 Run the full test suite (`python -m pytest --cov`) to validate causal behavior and confirm full backtest integration.
