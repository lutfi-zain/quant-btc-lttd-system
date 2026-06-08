## Context

This project implements a quantitative, statistically-grounded Bitcoin LTTD (Long-Term Trend Direction) trading system structured into a 6-layer pipeline. The legacy system directly averaged 12 correlated technical indicators without accounting for multicollinearity, resulting in 9 indicators having a Variance Inflation Factor (VIF) > 10. This caused inflated model confidence and synchronized failure risk during abrupt regime transitions. Layer 3 (Feature Processing) acts as a critical intermediary to transform raw, noisy, causal Layer 2 signals (`{-1, +1}`) into an orthogonal feature space before feeding them into the Layer 4 Ensemble Aggregation (L1-Lasso Logistic Regression).

## Goals / Non-Goals

**Goals:**
- Implement automated multicollinearity detection and pruning using a strict VIF threshold of 10.
- Implement PCA (Principal Component Analysis) orthogonalization to extract orthogonal components capturing >85% of variance from the raw indicator matrix.
- Calculate relative feature importance using Pratt's Measure (`dⱼ = βⱼ · rⱼ / R²`) to apportion R² appropriately among correlated features.
- Ensure the entire feature processing pipeline operates strictly causally, introducing absolutely zero lookahead bias into the walk-forward optimization (WFO).

**Non-Goals:**
- **No new indicators**: Adding new technical or on-chain indicators is explicitly out of scope for this layer.
- **No ensemble training**: Layer 3 prepares the data; it does not fit the final predictive model (which is strictly Layer 4's responsibility).
- **No full-history PCA**: Running standard PCA over the full dataset is explicitly prohibited as it introduces lookahead bias.

## Decisions

1. **Causal PCA via WFO Folds (No Static PCA)**
   - *Rationale*: Standard PCA on the full history leaks future variance into past components. To maintain causality, PCA fitting (and associated standard scaling) will be strictly confined to the training window of each Walk-Forward Optimization (WFO) fold. The test window will only be *transformed* using the fitted parameters.
   - *Alternatives*: Standard PCA (rejected due to lookahead bias); Relying solely on Layer 4 L1-Lasso to select features (rejected because high multicollinearity causes unstable Lasso coefficient paths).

2. **Strict VIF Pruning Before PCA**
   - *Rationale*: Even with PCA, extreme collinearity can warp the principal components. Implementing a pre-processing step that iteratively computes VIF and drops the feature with the highest VIF > 10 ensures the remaining matrix is well-conditioned.
   - *Alternatives*: Bypassing VIF and feeding everything into PCA (rejected because garbage-in/garbage-out applies to highly redundant indicators capturing the identical underlying momentum).

3. **Pratt's Measure for Feature Audit**
   - *Rationale*: Pratt's Measure isolates the relative importance of features despite correlation. It will be used post-execution to audit the legacy technical indicators, permanently removing features whose Pratt's Measure contribution is negligible.

## Risks / Trade-offs

- **[Risk] PCA Sign Ambiguity (Axis Flipping)** → *Mitigation*: PCA eigenvectors can arbitrarily flip signs across different WFO rolling windows, confusing the Layer 4 model. We will implement a sign-alignment heuristic (e.g., forcing the first principal component to always maintain a positive correlation with a baseline trend indicator like the raw 200-day moving average).
- **[Risk] Lookahead Bias via Scaling** → *Mitigation*: All feature standardizations (Z-score normalization required before PCA) must compute the mean and standard deviation strictly on the trailing data or the WFO train set. No global `scikit-learn` `StandardScaler` on the full dataframe.
- **[Risk] Computational Overhead** → *Mitigation*: Vectorize the VIF calculation using matrix inversion (`np.linalg.inv(corr_matrix)`) rather than running OLS regressions for every indicator pair.

## Migration Plan

1. **Implementation**: Create `src/features/vif.py`, `src/features/pca.py`, and `src/features/importance.py`.
2. **Integration**: Inject the `FeatureProcessor` class into the WFO pipeline runner between the Signal Engine output and the Ensemble Model input.
3. **Storage**: Update the `database/lttd.db` schema (via Layer 5) to persist both raw indicator scores and the orthogonalized PCA components for auditability and frontend visualization.
4. **Rollback**: If the PCA components produce lower out-of-sample Sharpe ratios during validation, we can easily toggle the pipeline to bypass PCA and use raw VIF-pruned indicators directly in the Lasso regression.

## Open Questions

1. **Window Size for Rolling Operations**: Should the causal PCA and VIF computations use an expanding window from inception, or a fixed rolling window matching the newly discovered optimal BTC uptrend detection context (800–1,200 days)?
2. **Handling On-Chain Metrics**: Should Layer 3 orthogonalize on-chain metrics (MVRV, NUPL, etc.) alongside technical indicators, or should on-chain metrics bypass PCA and be passed directly to the execution engine as pure regime filters? (Current hypothesis: Technicals go through PCA; On-chain metrics bypass).
