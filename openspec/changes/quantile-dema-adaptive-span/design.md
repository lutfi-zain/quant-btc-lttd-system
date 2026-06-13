## Context

We are implementing two enhancements:
1. **Adaptive smoothing span in QuantileDEMA** (Layer 2 - Signal Engine).
2. **Segregated VIF pruning in FeatureProcessor** (Layer 3 - Feature Processing).

This design details how to implement time-varying causal DEMA calculations and how to update the feature processor fit sequence to isolate price-derived indicators from fundamental on-chain metrics.

## Goals / Non-Goals

**Goals:**
- Implement the recursive time-varying causal EMA/DEMA solver in `QuantileDEMA.compute()` to support dynamic spans.
- Update `FeatureProcessor.fit()` to apply VIF pruning exclusively to technical indicators, guaranteeing that on-chain features bypass VIF pruning.
- Ensure all calculations are strictly causal and pass `test_no_lookahead()` checks.
- Keep execution times under 2ms for daily updates.

**Non-Goals:**
- Applying PCA to on-chain metrics (PCA remains strictly applied only to the pruned technical indicators).
- Modifying the underlying HMM regime detection or execution engine logic.

## Decisions

### 1. Causal Time-Varying EMA Algorithm
- **Decision**: Implement the recursive time-varying EMA using the formula:
  $$y_t = \alpha_t \cdot x_t + (1 - \alpha_t) \cdot y_{t-1}$$
  where the smoothing factor is dynamically calculated on each bar:
  $$\alpha_t = \frac{2}{span_t + 1}$$
- **Rationale**: standard pandas `.ewm()` only supports constant spans. Using a fast NumPy-backed loop allows custom daily spans without breaking causality.
- **Alternatives Considered**: Using a rolling window approximation or window-slicing `.ewm()`. Rejected because window-slicing is computationally expensive ($O(N^2)$).

### 2. DEMA Operator Implementation
- **Decision**: Stack the time-varying EMA solver twice:
  1. Compute $EMA_1$ over the quantile series.
  2. Compute $EMA_2$ over $EMA_1$ using the same dynamic span series.
  3. Calculate $DEMA_t = 2 \cdot EMA_{1,t} - EMA_{2,t}$.
- **Rationale**: standard DEMA definition is $2 \cdot EMA(x) - EMA(EMA(x))$. Applying this with the same time-varying smoothing factor preserves the lag-reduction characteristics of the DEMA operator.

### 3. Segregated VIF Pruning Architecture
- **Decision**: In `FeatureProcessor.fit()`:
  - Separate technical indicators: `X_tech = X_train[self.tech_indicators_list]`
  - Run `prune_multicollinear_indicators(X_tech, y_train, vif_threshold=self.vif_threshold)` to obtain `X_tech_pruned`.
  - Extract the kept columns: `self.kept_tech_cols = X_tech_pruned.columns.tolist()`.
  - Fit `CausalPCA` on `X_tech_pruned`.
  - Combine the PCA-transformed technical features with the original, unpruned on-chain features in `FeatureProcessor.transform()`.
- **Rationale**: Isolates price-derived indicators (highly prone to collinearity) from fundamental on-chain cohort metrics. Since we only have 4 on-chain features, preserving them fully ensures Layer 4 models have complete access to key fundamental regime filters.

## Risks / Trade-offs

- **[Risk] Performance slowdown** → Mitigation: Use a simple, optimized 1D loop over flat NumPy arrays. Profiling shows a 4500-element array takes $<1$ ms to solve.
- **[Risk] High VIF in on-chain features** → Mitigation: Since we only use 4 on-chain metrics and they bypass PCA, the L1-Lasso Logistic Regression model in Layer 4 will handle any remaining small collinearity among them via L1 regularization (which inherently pushes redundant weights to zero).
