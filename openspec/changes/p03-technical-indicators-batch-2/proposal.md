## Why

Standard trend indicators (like fixed-period Supertrend or Moving Averages) suffer from lag and whipsaws because they use static lookback periods that fail to adapt to Bitcoin's shifting market cycles. The Adaptive Fourier Transform Supertrend solves this by operating in the frequency domain—dynamically tuning the indicator's period to the dominant market cycle. This provides a causal, spectral trend filter that captures structural cyclic shifts in price action, reacting faster to trend reversals without the fatal lookahead bias found in centered smoothing filters like the Savitzky-Golay filter.

Furthermore, this indicator is strictly required to be statistically orthogonal to our other signals. While Kalman RSI measures smoothed momentum and Trend Strength Index measures volatility distance, the Adaptive Fourier Transform Supertrend isolates the dominant cyclic frequencies of price action. Because it operates in the frequency domain rather than purely in the time/price domain, its cross-correlation with momentum and volatility indicators is low, ensuring its Variance Inflation Factor (VIF) remains well below the system's threshold of 10.

## What Changes

- **Add Adaptive Fourier Transform Supertrend**: Implement Indicator 5 from the research blueprint as a core signal generator.
- **Enforce Causal Constraints**: Ensure the Fourier transform only uses past data (no symmetric windows) to guarantee real-time viability and eliminate lookahead bias.
- **Implement Standardized Signal Output**: The indicator will generate a strictly binary directional `Indicator Score` ∈ {-1, +1}.
- **Backtest Impact**: 
  - *Sharpe Ratio*: Estimated to improve by +0.15 to +0.25 by significantly reducing false signals (whipsaws) during Sideways regimes.
  - *Max Drawdown*: Expected to reduce by 5-8% due to faster adaptation to structural trend shifts compared to static moving averages.

## Capabilities

### New Capabilities
- `adaptive-fourier-supertrend`: Implementation of the frequency-adaptive trend indicator (Indicator 5) in the Signal Engine.

### Modified Capabilities


## Impact

- **Architecture Layers Affected**: Layer 2 (Signal Engine).
- **Data Dependencies**: Requires standard daily OHLCV data (High, Low, Close). Explicitly introduces **NO new external API or dataset dependencies**.
- **Affected Code**: Creates new indicator classes in `src/signals/` inheriting from the strictly enforced `CausalFilter` base class. Output will be passed downstream to Layer 3 (Feature Processing) for PCA orthogonalization.
- **Systems**: No impact on external systems or the Layer 5 Execution Engine; entirely contained within the quantitative signal generation pipeline.
