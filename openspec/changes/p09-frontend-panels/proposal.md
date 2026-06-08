## Why

To effectively monitor and validate the outputs of the quantitative pipeline, we need to visualize the statistical and mathematical properties of the system over time. The frontend panels will provide transparency into the HMM regime probabilities, PCA orthogonalization components, VIF pruning stability, and the final ensemble output score. Visualizing the divergence between price and orthogonalized indicators is essential for confirming the absence of lookahead bias and ensuring causal filter constraints are properly enforced in a live environment.

## What Changes

- Implement a primary dashboard with TradingView Lightweight Charts for daily LTTD final scores overlaying BTC price.
- Introduce a **Regime Panel** to display the 3-state HMM probabilities (Bull, Bear, Sideways) based on daily log returns and realized volatility.
- Introduce an **Indicator Matrix Panel** to show causal indicator scores ($\in \{-1, +1\}$) and PCA component weights.
- Introduce an **On-Chain Metrics Panel** displaying normalized BRK feeds (STH-MVRV, NUPL) compared against critical threshold levels.
- Add real-time visual assertions for VIF values to ensure no highly collinear indicators ($VIF > 10$) are bypassing the Layer 3 feature processing.
- Incorporate regime-weighted position sizing visualizations for the execution engine output.

## Capabilities

### New Capabilities

- `dashboard-lttd-chart`: Display the composite LTTD Final Score ($\in [-1.0, +1.0]$) with underlying asset price using TradingView Lightweight Charts.
- `regime-probability-panel`: Render the HMM posterior probabilities for Bull/Bear/Sideways market regimes over the 120-350 day epoch.
- `feature-diagnostics-panel`: Visualize indicator feature values, PCA variance explained, and VIF metrics to ensure multicollinearity bounds are respected.
- `onchain-metrics-panel`: Visualize BRK live data streams (STH-MVRV, STH-NUPL, STH-SOPR) mapping to causal filter outputs without lookahead bias.

### Modified Capabilities

*(None)*

## Impact

- **Affected Architecture Layer(s):** Layer 6 (Presentation). Relies on Layer 1-5 outputs.
- **Code & Dependencies:** Introduces React 18, TypeScript, Vite, and `lightweight-charts` to the `frontend/` directory (managed via `bun`). 
- **Data Dependencies:** Consumes REST endpoints from the Hono API backend. No new external data sources are introduced.

### Backtest Impact

This is a pure Presentation Layer visualization change. It has no impact on the underlying quantitative logic, WFO pipeline, or backtest execution.
- **Estimated Sharpe Ratio Impact:** 0.00
- **Estimated Max Drawdown Impact:** 0.00%

### Indicator Redundancy (VIF Argument)

This change does not introduce any new technical indicators. It strictly visualizes pre-existing signals output by Layer 2 and pruned by Layer 3, where VIF bounds are actively enforced.
