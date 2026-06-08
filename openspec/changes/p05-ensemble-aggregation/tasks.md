## 1. Feature Processing (Layer 3)

- [ ] 1.1 Create `src/features` package and initialization files
- [ ] 1.2 Implement `StandardScaler` utility for raw causal indicator normalization
- [ ] 1.3 Implement Variance Inflation Factor (VIF) computation for the indicator matrix
- [ ] 1.4 Implement VIF pruning logic to flag indicators with VIF > 10 (`vif_prune = True`) and explicitly log pruned count
- [ ] 1.5 Implement PCA orthogonalization to transform indicator scores into strictly orthogonal principal components
- [ ] 1.6 Implement validation to ensure cumulative explained variance of retained PCA components is >= 0.85
- [ ] 1.7 Add `pytest` unit tests for Feature Processing (VIF > 10 pruning and PCA explained variance >= 0.85 scenarios)

## 2. Walk-Forward Optimization Engine (WFO & CPCV)

- [ ] 2.1 Create `src/ensemble/wfo.py` module for cross-validation logic
- [ ] 2.2 Implement WFO rolling window generator enforcing strict precedence: 3yr train → 6mo validate → 6mo test
- [ ] 2.3 Implement Combinatorial Purged Cross-Validation (CPCV) splitting logic
- [ ] 2.4 Implement purging logic to remove training bars adjacent to test/validation boundaries (purge window size > 0)
- [ ] 2.5 Add `pytest` unit tests for WFO and CPCV to verify strict chronological window precedence and zero lookahead bias

## 3. Ensemble Aggregation Model (Layer 4)

- [ ] 3.1 Create `src/ensemble/model.py` module for Layer 4 logic
- [ ] 3.2 Implement L1-Lasso Logistic Regression model designed to ingest PCA-orthogonalized features
- [ ] 3.3 Implement scaling function to transform model predictions into a Final Score probabilistically bounded in `[-1.0, +1.0]`
- [ ] 3.4 Implement Pratt's Measure calculation (`dⱼ = βⱼ · rⱼ / R²`) for feature importance evaluation
- [ ] 3.5 Implement validation to guarantee the sum of Pratt's Measures equals 1.0 (100%) and individual measures are calculable
- [ ] 3.6 Integrate Layer 3 PCA outputs directly into the Layer 4 L1-Lasso training loops utilizing the WFO pipeline
- [ ] 3.7 Add `pytest` unit tests for Ensemble Aggregation (Final Score bounds and Pratt's Measure calculation scenarios)

## 4. System Integration & Verification

- [ ] 4.1 Create end-to-end integration test simulating data flow from Layer 2 → Layer 3 → Layer 4
- [ ] 4.2 Verify the WFO pipeline outputs and stores the out-of-sample test score R²
- [ ] 4.3 Run full test suite using `python -m pytest --cov` to ensure comprehensive test coverage across Layer 3 and 4
