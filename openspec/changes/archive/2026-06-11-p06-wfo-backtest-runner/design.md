## Context

The current LTTD (Long-Term Trend Direction) classification system relies on a quantitative pipeline mapping daily OHLCV and BRK on-chain metrics through an HMM (Layer 1) and ensemble model (Layer 4). Currently, there is no standardized, out-of-sample historical validation pipeline. Evaluating performance via static fitting on the entire dataset leads to overfitting, particularly given Bitcoin's shifting regime structures (e.g., the OU half-life expanding to 300+ days post-2020). 

To ensure the statistical soundness of our ensemble and its capability to adapt to changing regimes without lookahead bias, we are introducing a Walk-Forward Optimization (WFO) backtest runner. This component strictly partitions historical data into rolling windows (Train/Validate/Test) and integrates Combinatorial Purged Cross-Validation (CPCV) to eliminate serial correlation leakage. 

## Goals / Non-Goals

**Goals:**
- Implement a reproducible WFO pipeline utilizing a rolling 3-year train, 6-month validate, and 6-month test window.
- Integrate CPCV to purge training bars adjacent to the test boundary.
- Integrate with Layer 4 (Ensemble Aggregation) to support rolling `.fit()` and `.predict()` workflows.
- Abstract Layer 5 (Execution Engine) into a backtesting adapter that simulates portfolio outcomes (Sharpe, Max Drawdown, Hit Rate).
- Define the core backtest engine for the repository.

**Non-Goals:**
- Adding new technical indicators or on-chain metrics (VIF pruning constraints remain unchanged).
- Deploying live trading bots (the scope is strictly offline historical simulation).
- Creating new predictive architectures (the pipeline simulates the *existing* HMM + Logistic L1-Lasso logic).
- Intraday backtesting (the LTTD system operates on daily macro bars).

## Decisions

### 1. Backtest Engine Framework: `vectorbt` over `backtrader`
- **Rationale**: The LTTD pipeline is fundamentally a machine learning classification stack (HMMs, PCA, L1-Lasso). Data flows through Layer 1-4 as continuous matrices (pandas/numpy). `vectorbt` processes vectorized arrays natively and calculates portfolio metrics instantaneously. `backtrader` is event-driven (bar-by-bar), introducing an impedance mismatch with scikit-learn models and extreme performance bottlenecks for rolling ML refits.
- **Alternatives Considered**: 
  - `backtrader`: Rejected due to the slow `next()` event loop and difficulty handling external `pandas` DataFrames natively.
  - Custom loop: Rejected because calculating accurate portfolio metrics (Sortino, Sharpe, Max Drawdown) from scratch is error-prone.

### 2. CPCV and WFO Sliding Window Mechanic
- **Rationale**: We will implement a custom scikit-learn compatible CV iterator. The iterator will yield `(train_indices, test_indices)` where `test_indices` span 6 months. It will purge a blackout window $N$ (e.g., 30 days, or based on max autocorrelation lag) prior to and after the test set from `train_indices`. The total train lookback will strictly be 3 years (approx 1095 days).
- **Alternatives Considered**: 
  - `sklearn.model_selection.TimeSeriesSplit`: Rejected because it does not support purging adjacent bars, risking lookahead bias through serial correlation.

### 3. Layer 5 Adapter (Execution vs. Simulation)
- **Rationale**: Layer 5 currently executes trades by writing to a SQLite WAL database (`lttd.db`). The backtest runner will inject a `MockExecutionAdapter` into the pipeline. Instead of hitting SQLite, this adapter collects the final LTTD `Final Score` and HMM `Regime` into a daily `pandas.Series`, which is then passed to `vectorbt.Portfolio.from_signals()` to compute equity curves.
- **Alternatives Considered**: 
  - Using an in-memory SQLite database: Rejected because converting DB rows back to vectors for performance metrics adds unnecessary I/O overhead during massive WFO runs.

### 4. Handling Point-In-Time On-Chain Data
- **Rationale**: BRK on-chain metrics are retrieved with a `stamp` field. For accurate historical simulation without lookahead bias, we will merge BRK data onto the OHLCV dataframe using `pandas.merge_asof(direction='backward')` keyed on the `stamp`. This ensures the model at time $t$ only uses on-chain data that was computationally available at or before $t$.
- **Alternatives Considered**: 
  - Exact date joining: Rejected because on-chain data settlement may slip; `merge_asof` guarantees we only use strictly known prior data.

## Risks / Trade-offs

- **[Risk] High Computational Load from Rolling Fits** → **Mitigation**: Rolling a 3-year HMM and L1-Lasso every 6 months over a 10-year history yields ~20 separate training cycles. We will parallelize these WFO folds using Python's `concurrent.futures` or `joblib` since each fold is independent.
- **[Risk] Path Dependency in Feature Processing** → **Mitigation**: Layer 3 (Feature Processing) standard scalers and PCA transformations MUST be fit strictly on the 3-year training window of each fold and transformed on the test window. Fitting PCA globally prior to WFO will cause massive lookahead bias.
- **[Risk] Data Leakage via Indicator Window Size** → **Mitigation**: CPCV purging size $N$ must be dynamically evaluated or set conservatively (e.g., max window size of our Causal Filters) so that test data does not pollute the training set.

## Migration Plan

1. **Phase 1**: Introduce `src/backtest/wfo.py` containing the custom CPCV iterator.
2. **Phase 2**: Refactor Layer 4 (`src/ensemble/`) to expose a stateless `.fit(X, y)` and `.predict(X)` interface compatible with WFO folds.
3. **Phase 3**: Create the `src/backtest/runner.py` script that ties OHLCV data, Layer 4 models, and `vectorbt` together.
4. **Phase 4**: Add `test_no_lookahead()` and `test_cpcv_purging()` unit tests in the `tests/` suite.

*Rollback Strategy*: The backtest runner lives entirely within `src/backtest/`. If it introduces instability, it will not affect the live production inference paths in Layer 5 and `backend/index.ts`.

## Open Questions

- What should be the exact dynamic purging window size $N$ for CPCV? Should it match the longest Causal Filter lookback or the most recent HMM-inferred OU Half-Life?
- Will `vectorbt` handle regime-weighted position sizing natively via its size mapping arrays, or do we need to calculate raw target weights manually before passing to the portfolio constructor?
