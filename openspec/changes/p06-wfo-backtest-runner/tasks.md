## 1. CPCV and WFO Engine

- [ ] 1.1 Create `src/backtest/wfo.py` with `WFOIterator` to generate rolling windows: 3-year train, 6-month validate, and 6-month test
- [ ] 1.2 Implement Combinatorial Purged Cross-Validation (CPCV) to drop $N$ adjacent bars (up to 350 days) around the test window
- [ ] 1.3 Write `test_cpcv_purging()` in `tests/test_wfo.py` to mathematically verify absolute isolation of train and test splits

## 2. Refactor Ensemble Aggregation (Layer 4)

- [ ] 2.1 Refactor Layer 4 models to expose stateless `.fit(X, y)` and `.predict(X)` interfaces
- [ ] 2.2 Update Layer 3 (Feature Processing) to strictly fit PCA and standard scalers on the train window only, transforming the test window
- [ ] 2.3 Write tests to ensure Layer 4 L1-Lasso Logistic Regression and HMM properly fit and predict on standalone WFO splits

## 3. Historical Data Merging

- [ ] 3.1 Implement point-in-time data joining using `pandas.merge_asof(direction='backward')` keyed on the BRK `stamp` field
- [ ] 3.2 Ensure daily OHLCV and BRK merged datasets align perfectly with the inputs expected by the `WFOIterator`

## 4. Execution Simulation Adapter

- [ ] 4.1 Create `MockExecutionAdapter` that bypasses Layer 5 SQLite WAL operations
- [ ] 4.2 Configure `MockExecutionAdapter` to collect daily `Final Score` and HMM `Regime` states into a pandas DataFrame

## 5. Backtest Runner & Portfolio Metrics

- [ ] 5.1 Create `src/backtest/runner.py` leveraging `vectorbt.Portfolio.from_signals()` to map `MockExecutionAdapter` output to portfolio state
- [ ] 5.2 Implement Annualized Sharpe Ratio and Max Drawdown calculation using concatenated out-of-sample window returns
- [ ] 5.3 Implement Hit Rate (win rate) measurement partitioned by inferred HMM Regime (Bull, Bear, Sideways)
- [ ] 5.4 Implement parallelization using `concurrent.futures` or `joblib` to speed up independent WFO fold computations

## 6. Validation and End-to-End Testing

- [ ] 6.1 Create `test_no_lookahead()` to guarantee that indicators and model predictions at time $t$ remain identical when $t+1..t+N$ bars are added
- [ ] 6.2 Execute an initial end-to-end WFO historical simulation via `src/backtest/runner.py` to verify integration
- [ ] 6.3 Run `pytest --cov src/backtest/` to ensure testing requirements are met
