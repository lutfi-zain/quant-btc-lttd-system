## 1. Setup & Core Implementation

- [ ] 1.1 Update `QuantileDEMA` constructor and default `dema_span` parameter mapping in `src/signals/quantile_dema.py`
- [ ] 1.2 Implement the recursive time-varying causal EMA/DEMA solver in `src/signals/quantile_dema.py`
- [ ] 1.3 Modify `FeatureProcessor.fit()` in `src/features/processor.py` to isolate technical indicators from on-chain metrics during VIF pruning

## 2. Validation & Verification

- [ ] 2.1 Update unit tests in `tests/signals/test_quantile_dema.py` to check adaptive dema_span configurations
- [ ] 2.2 Add unit tests in `tests/features/test_processor.py` to verify segregated VIF pruning logic
- [ ] 2.3 Run pytest to verify all test cases pass and there is zero lookahead bias
