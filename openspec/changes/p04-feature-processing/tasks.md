## 1. Feature Processing Modules

- [ ] 1.1 Create `src/features/vif.py` with vectorized VIF calculation using matrix inversion (`np.linalg.inv(corr_matrix)`).
- [ ] 1.2 Implement iterative VIF pruning in `src/features/vif.py` to recursively drop the feature with the highest VIF > 10.0.
- [ ] 1.3 Create `src/features/pca.py` with strictly causal PCA fitting and scaling (fit on train window, transform test window).
- [ ] 1.4 Implement >85% variance retention threshold and sign-alignment heuristic in `src/features/pca.py`.
- [ ] 1.5 Create `src/features/importance.py` to calculate Pratt's Measure (`d_j = beta_j * r_j / R^2`).
- [ ] 1.6 Implement feature ranking and `< 0.01` (1%) contribution flagging in `src/features/importance.py`.

## 2. Orchestration and WFO Integration

- [ ] 2.1 Create `FeatureProcessor` class orchestrating VIF pruning, causal standardization, and PCA transformation.
- [ ] 2.2 Configure `FeatureProcessor` to apply PCA only to Technical Indicators and bypass On-Chain Metrics.
- [ ] 2.3 Integrate `FeatureProcessor` into the Walk-Forward Optimization (WFO) runner in Layer 4 (`src/ensemble/`).
- [ ] 2.4 Write `test_no_lookahead` unit tests to verify scaling and PCA projection leak zero future data.

## 3. Storage and Execution Interface

- [ ] 3.1 Update `database/lttd.db` schema to persist both raw indicator scores and orthogonalized PCA components.
- [ ] 3.2 Update Layer 5 (`src/execution/`) to receive and process the new orthogonalized feature structure.
- [ ] 3.3 Verify backend data pipeline writes the expanded feature set successfully at the daily level.
