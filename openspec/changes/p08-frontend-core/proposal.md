## Why

To provide statistical transparency and observability into the LTTD system, we need a frontend to visualize the HMM regime probabilities, PCA-orthogonalized feature components, and the final ensemble score over time. This ensures researchers can visually inspect real-time causal filter performance, monitor regime shifts, and verify the absence of lookahead bias in the execution outputs.

## What Changes

- Initialize a React 18 + TypeScript + Vite single-page application in the `frontend/` directory using `bun` as the package manager.
- Integrate TradingView Lightweight Charts to render BTC price action alongside the quantitative LTTD Final Score (range [-1.0, +1.0]).
- Build dashboard widgets to display the current system state, including the HMM inferred Regime (BULL / BEAR / SIDEWAYS) and individual causal indicator scores (∈ {-1, +1}).
- Implement an API client to fetch historical and real-time execution rows directly from the internal Hono v4 backend.
- **Architecture Layer**: This change exclusively affects Layer 6 (Presentation). It does not alter Layer 1-5 logic.
- **Mathematical/Statistical Motivation**: By plotting the outputs of the orthogonalized ensemble and causal indicators, we enable visual verification of the signal stability and WFO (Walk-Forward Optimization) behavior over the 120–350 day OU half-life epochs.
- **Backtest Impact**: None. This is a visualization layer only and does not impact the system's Sharpe ratio or maximum drawdown.
- **Data Dependencies**: Introduces no new external data dependencies. The frontend strictly consumes the internal Hono REST API which reads from `database/lttd.db`.
- **Redundancy/VIF**: No new technical or on-chain indicators are being added in this change.

## Capabilities

### New Capabilities
- `lttd-dashboard`: The primary user interface for monitoring HMM regimes, indicator scores, and the LTTD Final Score.
- `price-charting`: TradingView Lightweight Charts integration for rendering time-series data without lookahead bias.
- `frontend-api-client`: Data fetching layer to consume endpoints from the Layer 6 Hono backend.

### Modified Capabilities

## Impact

- **Affected Code**: Creates the foundational structure in the `frontend/` directory.
- **Architecture**: Completes Layer 6 (Presentation) of the pipeline.
- **Dependencies**: Adds React 18, TypeScript, Vite, and `lightweight-charts` via the `bun` package manager.
- **Systems**: Provides the visual interface for the system while maintaining strict separation of concerns from the Python quantitative execution engine.
