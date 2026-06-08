## Why

Bitcoin's market behavior is non-stationary, meaning that a static combination of indicators often overfits to past data and fails during structural market shifts (such as the expansion to a 300+ day OU half-life in the post-2020 institutional era). By implementing a 3-state Hidden Markov Model (HMM) trained on daily log returns and realized volatility, we solve the problem of synchronized failure during market transitions. This change establishes the foundational Regime Detection layer (Layer 1) to dynamically classify the macro environment as BULL, BEAR, or SIDEWAYS, providing a robust statistical prior for dynamic position sizing without relying on correlated technical indicators.

## What Changes

- **HMM Pipeline**: Implement a 3-state Gaussian Hidden Markov Model using `hmmlearn` to infer latent market regimes.
- **Feature Computation**: Calculate daily log returns and realized volatility as the sole input features for the HMM.
- **Layer 1 Construction**: Create the `src/regime/` module, ensuring strict separation of concerns (zero dependency on the Signal Engine or price indicators).
- **Orthogonality & VIF**: Because the HMM relies purely on returns and volatility rather than moving averages or momentum, it acts as an orthogonal regime filter rather than a redundant technical indicator, ensuring zero Variance Inflation Factor (VIF) overlap with Layer 2 signals.
- **Data Dependency**: Introduces an internal dependency on historical daily OHLCV (specifically close prices) to compute the necessary log returns and realized volatility. No new external API dependencies are introduced by this specific change.

### Backtest Impact
This regime detection capability is estimated to significantly improve the system's risk-adjusted returns by scaling down exposure during BEAR and SIDEWAYS regimes. We estimate an improvement in the Sharpe ratio and a reduction in max drawdown by approximately 15-25% compared to static trend-following models.

## Capabilities

### New Capabilities
- `hmm-regime-classification`: Defines the training pipeline, feature preparation (log returns and realized volatility), and inference logic for the 3-state Hidden Markov Model.

### Modified Capabilities
*(None)*

## Impact

- **Architecture Layers**: Affects Layer 1 (Regime Detection). Provides regime state outputs that will later be consumed by Layer 5 (Execution Engine).
- **Codebase**: Creates the new `src/regime/` module for the project.
- **Dependencies**: Relies on `hmmlearn`, `scikit-learn`, `pandas`, and `numpy` from the defined ML stack.
