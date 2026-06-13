## Why

To ensure optimal feature stability and signal robustness, we propose two core enhancements to the LTTD trading system:

1. **Adaptive QuantileDEMA Smoothing Span**:
   Currently, `QuantileDEMA` uses a static `dema_span=200`. The recent statistical audit revealed that `QuantileDEMA` is the technical indicator closest to non-stationarity ($p$-value = 0.0232). Using a static smoothing window on a time-series with a dynamic trend reversion speed (OU half-life ranging from 120 to 350 days) introduces lag during fast-reverting periods and whipsaws in sideways regimes. Scaling `dema_span` dynamically with the resolved lookback window aligns smoothing with the market's empirical regime speed, improving stationarity and signal coherence.

2. **Segregated VIF Pruning in Feature Processor**:
   Currently, `FeatureProcessor` runs VIF pruning on all features combined (technical indicators + on-chain metrics). Because on-chain metrics (e.g., STH-MVRV rate of change) correlate with short-term price momentum, they are vulnerable to being pruned when combined with technical indicators in a single VIF matrix. Since on-chain metrics represent fundamental blockchain holder cohort valuations, dropping them due to temporary price correlation degrades the quality of Layer 4 ensemble models. Segregating VIF pruning to run strictly on the 6 price-derived technical indicators preserves the fundamental on-chain feature matrix while still removing price momentum redundancies.

## What Changes

We will implement the following changes:
1. **Adaptive QuantileDEMA**:
   - Update `QuantileDEMA` in `src/signals/quantile_dema.py` to allow `dema_span` to default to `None` (resolved dynamically to match the lookback window).
   - Implement a causal, recursive time-varying EMA solver in Python to calculate the DEMA smoothing series using bar-specific alpha coefficients:
     $$\alpha_t = \frac{2}{\text{span}_t + 1}$$
2. **Segregated VIF Pruning**:
   - Modify `FeatureProcessor.fit()` in `src/features/processor.py` to separate technical indicators from on-chain metrics during fitting.
   - Run VIF pruning strictly on the `tech_indicators_list` sub-matrix, leaving the on-chain features unpruned.
3. **Tests**:
   - Update unit tests to verify the causality, stationarity, and correctness of both the adaptive DEMA smoothing and the segregated VIF pruning logic.

## Capabilities

### New Capabilities
*None*

### Modified Capabilities
- `technical-indicators`: Enhanced the `QuantileDEMA` indicator requirement to dynamically scale its double exponential smoothing operator (`dema_span`) with the active lookback window to adapt to the market's empirical regime speed.
- `feature-processor`: Updated the feature processing requirements to isolate technical indicators from on-chain metrics during VIF pruning, ensuring fundamental on-chain features are preserved in the output.

## Impact

- **Affected Layers**: Layer 2 (Signal Engine) and Layer 3 (Feature Processing).
- **Data Dependencies**: None. Uses existing historical daily data.
- **Ensemble Stability**: Segregated VIF pruning ensures that the L1-Lasso Logistic Regression and PCA Consensus models always receive complete on-chain cohort inputs, stabilizing the final macro LTTD prediction.
- **Backtest Impact**: Reduces drawdown whipsaws in sideways markets and increases out-of-sample Sharpe ratio.
