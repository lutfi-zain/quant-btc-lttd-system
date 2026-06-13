## Why

The current frontend needs to effectively communicate the complex outputs of the 5-layer LTTD pipeline (Regime, Signals, Feature Processing, Ensemble Aggregation). A premium, professional dashboard interface similar to Swissblock or Capriole Investments is necessary to visualize macro directional bias (Bull/Bear/Sideways), causal indicator scores, and the final ensemble score. This improves the operator's ability to monitor real-time statistical properties and execution triggers without being overwhelmed by raw data.

**Mathematical/Statistical Motivation:** While this is a UI change, it directly addresses the need to present orthogonal ensemble outputs and HMM regime probabilities in a statistically coherent manner. Visualizing PCA-weighted indicators requires a clean, structured interface to prevent misinterpretation of multicollinear signals vs orthogonal components.

## What Changes

- Complete redesign of the React SPA (Layer 6: Presentation) to adopt a premium, institutional-grade dashboard aesthetic.
- The redesign will use the `stitch` MCP to generate and apply a high-end design system tailored to quantitative dashboards.
- Introduction of specialized widgets for:
  1. HMM Regime Probabilities (Bull/Bear/Sideways).
  2. Final Ensemble LTTD Score [-1.0, +1.0] gauge.
  3. Feature Heatmap for orthogonalized indicator scores.

**Architecture Layers Affected:** Layer 6: Presentation (Frontend).

**Backtest Impact:** No direct impact on Sharpe ratio or max drawdown, as this does not alter the underlying model or execution logic. However, it improves operational reliability and monitoring.

**Data Dependencies:** No new backend data dependencies. The frontend will consume the existing Hono API endpoints. May introduce new frontend UI libraries (e.g., Radix UI, Tailwind if specified, or vanilla CSS based on Stitch design system).

## Capabilities

### New Capabilities
- `dashboard-ui`: A premium, Swissblock/Capriole-style dashboard interface for monitoring the LTTD system outputs.

### Modified Capabilities
- `frontend-presentation`: Existing frontend presentation logic is fully revamped to use the new design system.

## Impact

- `frontend/`: Complete rewrite of UI components and layouts.
- `backend/`: No changes expected; endpoints remain the same.
- `database/lttd.db`: No changes.
