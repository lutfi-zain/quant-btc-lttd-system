## Why

The quantitative trading system requires a robust validation pipeline to assess the true out-of-sample performance of the LTTD classification model. Currently, static fitting on the full historical dataset overfits to past market regimes, which fails to capture Bitcoin's shifting structural dynamics (e.g., the expansion of the OU half-life to 300+ days post-2020). By implementing a Walk-Forward Optimization (WFO) backtest runner with Combinatorial Purged Cross-Validation (CPCV), we mathematically isolate training data from test data. This rolling adaptation approach prevents lookahead bias and eliminates over-optimistic performance reporting, providing a statistically sound measure of the system's predictive edge.

## What Changes

- Implement a dedicated historical backtest orchestration script (`src/backtest/runner.py`) utilizing Walk-Forward Optimization (WFO).
- Introduce sliding window logic for model training: rolling 3-year train, 6-month validate, and 6-month test windows.
- Apply Combinatorial Purged Cross-Validation (CPCV) to purge training bars adjacent to test windows, mathematically ensuring no leakage of serial correlation.
- Enforce strict separation between historical simulation and live execution logic.
- *Note:* This change does not add any new technical or on-chain indicators; thus, it inherently preserves the existing PCA orthogonalization and VIF < 10 constraints in Layer 3.

## Backtest Impact

Since this feature introduces the backtesting infrastructure itself, it serves as the baseline measurement tool for all future system modifications. By shifting from a static full-history fit to a rigorous out-of-sample WFO pipeline, the reported out-of-sample Sharpe ratio is expected to be more conservative and realistic. Max drawdown will be accurately identified across shifting macro regimes (e.g., pre-2017 vs. post-2020).

## Capabilities

### New Capabilities
- `wfo-backtest-runner`: Orchestrates the Walk-Forward Optimization pipeline, rolling windows, and CPCV purging logic across historical data.
- `performance-metrics`: Computes and aggregates out-of-sample quantitative metrics including Sharpe ratio, maximum drawdown, and hit rate.

### Modified Capabilities

## Impact

- **Affected Architecture Layers**: 
  - **Layer 4 (Ensemble Aggregation)**: Requires updates to support rolling model fits over expanding/sliding windows instead of single static fits.
  - **Layer 5 (Execution Engine)**: Requires an adapter to simulate historical executions rather than writing to the live SQLite WAL database.
- **Dependencies**: Relies on existing libraries like `pandas`, `scikit-learn` and potentially `vectorbt`/`backtrader` as defined in the architecture, without introducing new external packages.
- **Data Dependency**: Explicitly introduces **NO new data dependency** (API, dataset, or feature). It operates entirely on the existing historical price data and BRK on-chain metrics.
