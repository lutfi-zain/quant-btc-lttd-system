## 1. Implement Strict Regime Vocabulary

- [x] 1.1 Map HMM outputs in `src/regime/filter.py` or `src/pipeline.py` to strictly use `BULL`, `BEAR`, or `SIDEWAYS`.
- [x] 1.2 Update regime-dependent Execution Engine logic (`src/execution/engine.py` or `src/execution/sizing.py`) to align with the mapped 3 states if necessary.
- [x] 1.3 Add tests to verify that the regime inference strictly returns `BULL`, `BEAR`, or `SIDEWAYS`.

## 2. Eliminate Dummy Variable Trap

- [x] 2.1 Update feature matrix construction in `src/pipeline.py` to drop the `p_sideways` column before feeding to the Ensemble Aggregation layer.
- [x] 2.2 Validate feature matrix in `tests/test_pipeline.py` ensures `p_sideways` is not passed to the ensemble models.

## 3. Dynamic VIF Pruning for On-Chain Metrics

- [x] 3.1 Modify `src/features/vif.py` to iteratively compute VIF on on-chain features and drop those with VIF > 10 (keeping the most predictive one, e.g., `sth_mvrv` over `sth_nupl`).
- [x] 3.2 Update `src/pipeline.py` to invoke this dynamic VIF filtering over the complete on-chain feature set.
- [x] 3.3 Add unit test in `tests/features/test_vif.py` mocking high collinearity between two inputs and validating that the pipeline successfully drops one.

## 4. Backtesting & Validation

- [ ] 4.1 Run the walk-forward backtest (`python -m src.backtest.runner --start 2017-01-01 --end 2026-06-01`) to confirm improvements in Sharpe Ratio (>1.0) and Max Drawdown.
- [ ] 4.2 Run full test suite (`python -m pytest --cov`) to ensure no regressions and >90% coverage.
