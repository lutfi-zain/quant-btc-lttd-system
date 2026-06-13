## ADDED Requirements

### Requirement: quantile-dema-dynamic-span-support
The `QuantileDEMA` indicator SHALL support a dynamic time-varying double exponential smoothing span (`dema_span`) that is determined on a bar-by-bar basis from the resolved lookback window series.

#### Scenario: resolve-time-varying-dema-span
- **WHEN** the `dema_span` parameter is initialized to `None` in `QuantileDEMA`
- **THEN** it SHALL resolve the daily smoothing spans dynamically to match the resolved lookback series (clamped between 120 and 350 days).

---

### Requirement: dynamic-span-causality-invariance
The dynamic double exponential moving average (DEMA) solver inside `QuantileDEMA` SHALL run as a strictly causal recursive filter, referencing only historical and current values.

#### Scenario: verify-dynamic-dema-causality
- **WHEN** computing indicator scores with a time-varying `dema_span` on truncated data $X_{1 \dots t}$ and on full data $X_{1 \dots T}$
- **THEN** the value at index $t$ SHALL remain identical: $S_t = S'_t$.

---

### Requirement: dynamic-dema-value-bounds
The final calculated indicator scores of `QuantileDEMA` under dynamic span configurations SHALL be strictly bounded in $[0.0, 1.0]$.

#### Scenario: check-dynamic-dema-score-bounds
- **WHEN** running `QuantileDEMA` with a time-varying `dema_span` on the historical daily BTC dataset
- **THEN** every computed indicator score $S_t$ SHALL lie in the range $[0.0, 1.0]$ and the number of NaNs after the stabilization period (first 350 bars) SHALL be zero.

---

### Requirement: segregated-vif-pruning-in-processor
The `FeatureProcessor` SHALL run VIF pruning strictly on price-derived technical indicators, ensuring that fundamental on-chain metrics bypass VIF pruning and are preserved in the final feature matrix.

#### Scenario: run-segregated-vif-pruning
- **WHEN** fitting the `FeatureProcessor` on a training matrix containing both technical indicators and on-chain features
- **THEN** only technical indicators with VIF > threshold are pruned, and all 4 on-chain features are preserved in the final processed output.
