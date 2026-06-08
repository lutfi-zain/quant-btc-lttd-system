## Why

The legacy system hardcodes historical on-chain metrics into static arrays, which silently fails (returning a score of 0) for out-of-sample data during live execution. By introducing the `brk-client` to fetch real-time on-chain data (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`) from the `bitview.space` API, we ensure statistical validity, prevent data staleness, and allow the Walk-Forward Optimization (WFO) and HMM regime filters to operate on accurate, up-to-date market states.

## What Changes

- Implement a Python data fetcher using `brk-client` to retrieve daily on-chain metrics from the `bitview.space` API.
- Introduce validation logic to assert that the `stamp` field from the API response is no older than 1 day before passing the data to the ensemble or regime filters.
- **BREAKING**: Remove all legacy hardcoded `F1_data` through `F4_data` arrays from the signal processing pipeline.
- Expose bulk-fetching and latest-value fetching utilities for integration into the Walk-Forward Optimization pipeline.

## Capabilities

### New Capabilities
- `brk-api-client`: Fetches and validates live and historical on-chain metrics (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`) using the open-source BRK API, ensuring data freshness and integrity for statistical modeling.

### Modified Capabilities

## Backtest Impact

- **Sharpe Ratio & Max Drawdown**: No change expected for historical in-sample backtests, since the API provides the exact same values as the hardcoded arrays for the past. However, out-of-sample performance will be completely restored, preventing the silent degradation (artificial 0 scores) that would otherwise skew live drawdown calculations and Sharpe ratios to baseline holding metrics.

## Impact

- **Architecture Layers Affected**: 
  - Layer 1: Regime Detection (receives live on-chain data for regime filtering).
  - Layer 2: Signal Engine (ingests fresh on-chain metrics instead of static arrays).
- **Data Dependencies**: Introduces a new external data dependency on the `bitview.space` API via the `brk-client` pip package. No API keys or authentication are required.
- **Affected Code**: `src/signals/` and `src/regime/` will be updated to consume the `brk-client` interface instead of static arrays.
- **Mathematical/Statistical Motivation**: Hardcoded arrays truncate the time-series, destroying the statistical properties (mean, variance, distribution) of the on-chain variables in real-time execution. Live fetching restores the structural integrity of the inputs, ensuring the PCA and L1-Lasso models receive properly distributed features without lookahead bias.
