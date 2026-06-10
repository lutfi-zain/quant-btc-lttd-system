## Context
The legacy Pine Script system relied on an ensemble of 12 highly correlated technical indicators, which led to synchronized failures during market regime shifts due to severe multicollinearity. Previous batches successfully implemented orthogonal indicators for momentum and spectral frequencies. However, the system still lacks features capable of capturing the topological randomness of the price series and handling heavy-tailed return distributions. 
Batch 3 introduces three new indicators: Fractal Dimension Index (FDI), Quantile DEMA, and Advanced Stochastic. This batch focuses on replacing the removed non-causal oscillators (Indicators 4, 8, and 10) with statistically rigorous, causally-filtered alternatives.

## Goals / Non-Goals

**Goals:**
- Implement the Fractal Dimension Index (FDI) to quantify the structural randomness of Bitcoin's price action.
- Implement the Quantile DEMA Trend to handle heavy-tailed price distributions using robust quantile regression bands.
- Implement an Advanced Stochastic oscillator for strictly causal, bounded exhaustion detection to pinpoint macro-reversals.
- Enforce the `CausalFilter` base class constraint on all three indicators to guarantee zero future data leakage.
- Generate deterministic indicator outputs $\in \{-1, +1\}$ to feed directly into the Layer 3 Feature Processing pipeline.

**Non-Goals:**
- Adjusting the Layer 1 HMM Regime Detection or Layer 4 Ensemble Aggregation models.
- Changing the PCA orthogonalization logic or VIF pruning thresholds in Layer 3.
- Introducing new external data dependencies or APIs (calculations will depend strictly on local OHLCV feeds).

## Decisions

### 1. Fractal Dimension Index (FDI) Mechanism
**Decision:** We will calculate the FDI using Sevcik's algorithm over a rolling causal window. Because Layer 2 strictly requires outputs $\in \{-1, +1\}$, the pure FDI value ($D \in [1, 2]$) will act as an efficiency filter coupled with a trend baseline (e.g., EMA). When $D < 1.5$ (trending), the signal outputs `+1` or `-1` aligned with the trend. When $D \geq 1.5$ (mean-reverting), the signal will maintain its previous state or trigger a counter-trend reversal based on distance from the mean.
**Rationale:** A standalone FDI provides magnitude/efficiency but not direction. By pairing it with a simple causal baseline, we generate a highly predictive directional signal that automatically dampens false breakouts in sideways regimes.
**Alternatives Considered:** Passing the continuous $D$ score into the ensemble. *Rejected* because Layer 2's API contract dictates discrete $\{-1, +1\}$ outputs to ensure standardized orthogonalization.

### 2. Quantile DEMA Calculation Method
**Decision:** The Quantile DEMA will compute rolling causal quantiles (e.g., 90th and 10th percentiles of the closing price distribution) and apply the DEMA operator ($2 \times \text{EMA} - \text{EMA}(\text{EMA})$) to those quantiles. This produces asymmetric trend bands.
**Rationale:** Crypto returns have heavy tails, causing mean-based smoothing (like standard EMA) to lag or distort. Using quantiles provides a robust, non-parametric baseline that ignores extreme outlier wicks while quickly adapting to structural shifts. A breakout above the DEMA upper quantile triggers `+1`, and below the lower quantile triggers `-1`.
**Alternatives Considered:** Applying a standard DEMA with a wide standard deviation multiplier (Bollinger style). *Rejected* because standard deviation assumes a normal distribution, which is invalid for BTC log returns.

### 3. Advanced Stochastic Logic
**Decision:** The Advanced Stochastic will compute $\%K$ using a dynamically adjusting lookback window scaled by a causal volatility measure (like ATR). The signal line ($\%D$) will be smoothed using a purely causal Exponential Moving Average (EMA) rather than a simple moving average.
**Rationale:** A static-window Stochastic breaks across different macro regimes. Volatility-scaled windows ensure the bounds properly encapsulate true exhaustion zones. It will trigger `-1` when crossing below an overbought threshold and `+1` when crossing above an oversold threshold.
**Alternatives Considered:** Smoothing the Stochastic using a Savitzky-Golay Filter (SGF). *Rejected* because SGF introduces severe lookahead bias, invalidating backtests.

## Risks / Trade-offs

- **[Risk] High Computational Complexity:** Calculating rolling fractals (Sevcik's algorithm) and rolling quantiles in Python pandas can be computationally expensive and may slow down the WFO backtester.
  → **Mitigation:** Rely on vectorized NumPy strided array operations. If performance degrades beyond the budget, consider integrating Numba for the sliding window logic.
- **[Risk] Whipsawing in Borderline Regimes:** As the FDI oscillates directly around 1.5, it may cause the signal engine to flip rapidly between trend-following and mean-reverting states.
  → **Mitigation:** Implement a small hysteresis band (e.g., $1.45$ to $1.55$) in the FDI decision tree to prevent rapid toggling, and rely on Layer 1's regime weighting to suppress volatile signals.

## Migration Plan

1. **Implementation:** Create the three signal classes in `src/signals/` inheriting from the `CausalFilter` base class.
2. **Testing:** Write `pytest` unit tests for each indicator. Most importantly, assert `test_no_lookahead()` passes to verify zero data leakage.
3. **Integration:** Hook the new indicators into the Layer 3 feature matrix.
4. **Validation:** Run VIF analysis ensuring the new signals' Variance Inflation Factors remain below 10 relative to Batch 1 and 2 indicators.
5. **Rollback Strategy:** If severe multicollinearity is detected (VIF > 10), apply Pratt's Measure to isolate the redundant feature and drop it prior to PCA orthogonalization.

## Open Questions

- What are the optimal default causal window sizes for the FDI and Advanced Stochastic? (To be empirically determined during the initial Walk-Forward Optimization runs).
- For the Advanced Stochastic, what is the exact ATR scaling function for the dynamic lookback window? (Requires tuning to prevent excessively long windows during high-volatility spikes).
