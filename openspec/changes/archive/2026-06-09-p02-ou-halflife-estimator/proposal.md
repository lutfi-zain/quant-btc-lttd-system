## Why

Bitcoin's Ornstein-Uhlenbeck (OU) mean-reversion half-life is strictly epoch-dependent, having structurally expanded from 40–80 days (pre-2017) to over 300 days in the post-2020 institutional era. Relying on a fixed lookback window (e.g., 200 days) for trend detection creates phase lag during mean-reverting regimes and premature exits during trending regimes; dynamically estimating the OU Half-Life allows us to mathematically align the LTTD epoch window (120–350 days) with current market realities.

## What Changes

- **Statistical Motivation**: Implement an Ornstein-Uhlenbeck stochastic process calibration to estimate the mean-reversion speed of daily log returns. This provides an empirical basis for setting window sizes, replacing arbitrary scalar lookbacks with a statistically derived meta-parameter.
- **Dynamic Causal Filters**: Update the base `CausalFilter` to accept dynamically adjusting window bounds (restricted to 120–350 days) governed by the prevailing OU Half-Life.
- **Architecture Layers**:
  - **Layer 3 (Feature Processing)**: Houses the new OU Half-Life calculation module.
  - **Layer 2 (Signal Engine)**: Consumes the metric to resize historical context windows for all Technical Indicators in real-time.
- **Redundancy & VIF**: The OU Half-Life is a structural meta-parameter, not a direct directional signal. Because it modulates lookbacks rather than acting as an additive feature in the Ensemble Aggregation, it has zero multicollinearity (VIF = 0) with existing directional signals.
- **Data Dependency**: No new external data dependencies are introduced. The estimator relies exclusively on existing OHLCV daily log returns.
- **BREAKING**: Historical backtests using fixed lookback parameters will no longer match. WFO (Walk-Forward Optimization) pipelines must be updated to recalibrate the OU Half-Life quarterly.

## Capabilities

### New Capabilities
- `ou-halflife-estimator`: Calculates the rolling Ornstein-Uhlenbeck mean-reversion half-life using historical log-returns to determine the optimal macroeconomic lookback window for the current epoch.
- `dynamic-signal-windows`: Enables causal filters to dynamically adapt their context windows (120-350 days) in real-time based on the OU half-life, explicitly enforcing zero Lookahead Bias.

### Modified Capabilities

## Impact

- **Affected Code & APIs**: 
  - `src/signals/` base classes will be updated to accept dynamic window arguments.
  - `src/features/` will receive new statistical logic for the OU calibration.
- **Backtest Impact**: 
  - **Sharpe Ratio**: Expected to improve WFO Sharpe ratio by adapting to accelerated mean-reversion environments faster.
  - **Max Drawdown**: Anticipated to reduce maximum drawdown by preventing delayed signal crossovers during violent macroeconomic Regime shifts.
