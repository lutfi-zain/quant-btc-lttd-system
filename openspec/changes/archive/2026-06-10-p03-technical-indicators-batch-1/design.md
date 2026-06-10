## Context
The legacy Pine Script LTTD system relied on 12 correlated technical indicators and a Savitzky-Golay filter that used centered/symmetric windows, introducing significant lookahead bias. This resulted in artificially inflated backtest performance and synchronized failures during live regime shifts. To align with the mathematically grounded 6-Layer Architecture, we need to rebuild Layer 2 (Signal Engine). The new Signal Engine must generate binary directional signals (`Indicator Score` $\in \{-1, +1\}$) that are strictly causal (only referencing current and past bars) and mathematically orthogonal to avoid multicollinearity.

## Goals / Non-Goals

**Goals:**
- Design a generic `CausalFilter` base class to enforce real-time constraints across all technical indicators.
- Implement the first batch of mathematically distinct technical indicators: Kalman RSI (Momentum), Adaptive Fourier Supertrend (Spectral Frequency), and Trend Strength Index (Volatility-Adjusted Distance).
- Ensure all technical indicators process OHLCV data to output a strict $\{-1, +1\}$ directional score.
- Ensure that the resulting signals capture distinct market dimensions, minimizing multicollinearity to achieve a Variance Inflation Factor (VIF) $< 10$.

**Non-Goals:**
- Integration of on-chain metrics (these will be handled in a separate change/batch).
- Implementation of Layer 4 Ensemble aggregation and Walk-Forward Optimization (WFO).
- Final PCA orthogonalization implementation (this occurs strictly in Layer 3: Feature Processing).
- Over-optimizing indicator parameters (hyperparameter tuning will occur downstream during WFO).

## Decisions

1. **`CausalFilter` Base Architecture**
   - *Decision:* Create an abstract base class `CausalFilter` in `src/signals/` that defines a standard interface `compute(ohlcv: pd.DataFrame) -> pd.Series` outputting $\{-1, +1\}$.
   - *Alternatives Considered:* Writing functional indicators without a class hierarchy.
   - *Rationale:* An abstract base class enforces the structural requirement of returning binary signals and allows us to enforce a standardized `test_no_lookahead` unit test across all indicators, ensuring zero lookahead bias by design.

2. **Kalman RSI for Momentum Extraction**
   - *Decision:* Apply a 1D Kalman filter recursively to a standard 14-period RSI to track the hidden momentum state.
   - *Alternatives Considered:* Exponential Moving Average (EMA) of RSI or a Savitzky-Golay filter.
   - *Rationale:* EMA introduces excessive lag, delaying regime shift detection. The legacy Savitzky-Golay filter inherently introduced lookahead bias via symmetric windows. The Kalman filter provides a statistically sound, zero-lag recursive estimate of the hidden state, ensuring strict causality.

3. **Adaptive Fourier Transform Supertrend for Spectral Frequency**
   - *Decision:* Utilize a sliding Short-Time Fourier Transform (STFT) to identify the dominant cycle frequency and dynamically scale the Supertrend lookback parameters.
   - *Alternatives Considered:* Standard fixed-period Supertrend or Hilbert Transform.
   - *Rationale:* A fixed-period Supertrend fails when the market's structural behavior shifts (e.g., BTC's OU Half-Life expanding post-2020). An adaptive Fourier approach continuously measures the dominant frequency, making the indicator robust against expanding or contracting market cycles.

4. **Trend Strength Index (VWMA-ATR Distance)**
   - *Decision:* Compute the normalized distance between the closing price and the Volume-Weighted Moving Average (VWMA), scaling the distance using the Average True Range (ATR).
   - *Alternatives Considered:* Average Directional Index (ADX) or basic MA crossovers.
   - *Rationale:* Basic moving averages ignore volume conviction. By utilizing VWMA and normalizing by ATR, we quantify trend strength relative to current market volatility. This captures a unique statistical dimension compared to RSI and Spectral analysis, guaranteeing distinct features and a low VIF.

## Risks / Trade-offs

- **[Risk] Kalman Filter Initialization Transients** → *Mitigation:* Apply a burn-in period (e.g., 50 days) where the indicator outputs a neutral state ($0$) or carries forward a naive prior until the state covariance converges.
- **[Risk] Adaptive Fourier Transform Instability** → *Mitigation:* Restrict the detected dominant cycle frequency to a realistic bounded range (e.g., 14 to 120 days) to prevent extreme parameter shifts during flash crashes.
- **[Risk] Implicit Lookahead Bias in Pandas** → *Mitigation:* The `CausalFilter` base class will be paired with a mandatory `test_no_lookahead()` unit test. This test will verify that appending future data points does not alter historical indicator outputs.

## Migration Plan

- **Deployment Steps:** 
  1. Add `CausalFilter` in `src/signals/base.py`.
  2. Implement `KalmanRSI`, `AdaptiveFourierSupertrend`, and `TrendStrengthIndex`.
  3. Create test files covering edge cases and causality.
  4. Run `python -m pytest -xvs` and `python -m pytest --cov` to validate execution and test coverage.
- **Rollback Strategy:** Since this change introduces net-new code to Layer 2 and does not overwrite existing pipelines in production, rollback is simply reverting the PR if tests fail or performance degrades in backtests.

## Open Questions

- Should the Kalman Filter covariance matrices ($Q$ and $R$) be static hyperparameters tuned to historical BTC volatility, or dynamically updated?
- What is the optimal sliding window length for the Adaptive Fourier Transform to balance responsiveness with spectral resolution? (Current hypothesis is between 60 and 90 days).
