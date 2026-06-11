## Why

The quantitative LTTD (Long-Term Trend Direction) trading system operates on a 6-layer architecture. Layers 1 through 5 handle statistically-grounded computations—ranging from the 3-state HMM Regime detection (on daily log returns and realized volatility), causal signal generation, PCA orthogonalization with VIF pruning, to L1-Lasso Logistic Regression ensemble aggregation, and finally position sizing execution. 

To maintain strict architectural boundaries, the presentation of these computed metrics (Final Score, Regime, Top Indicators) must be decoupled from the core quantitative pipeline. This proposal designs the Layer 6: Presentation (Backend API). By exposing these metrics via standard REST endpoints using Hono v4 on the Bun runtime, we enable the frontend SPA to cleanly consume and visualize the daily LTTD output without direct exposure to the underlying Python/statistical execution engine.

**Mathematical/Statistical Motivation:** 
This change does not introduce new statistical models or indicators. Instead, it ensures the statistically-grounded data computed by Layer 4 (Ensemble Aggregation) and Layer 5 (Execution Engine) is securely and efficiently served. It preserves the integrity of the Final Score (∈ [-1.0, +1.0]) and Regime (Bull / Bear / Sideways) classifications without risking lookahead bias or computation interference during data retrieval.

## What Changes

We are introducing the Backend API component for Layer 6 (Presentation). Specifically:
- **Hono v4 on Bun**: Setting up a new lightweight, high-performance API server in `backend/index.ts` using the Bun runtime.
- **SQLite Integration**: Creating read-only queries connecting to `database/lttd.db` (configured in WAL mode) to serve the Daily LTTD rows.
- **REST Endpoints**: 
  - `GET /api/health`: Health check endpoint.
  - `GET /api/lttd/latest`: Fetches the most recent daily LTTD record (timestamp, Final Score, Regime, Top Indicators).
  - `GET /api/lttd/history`: Bulk fetches historical daily LTTD records for time-series charts.

**Architecture Layers Affected:** 
- Layer 6: Presentation

**New Data Dependencies:** 
This change reads exclusively from the existing local `database/lttd.db`. It does not introduce any new external API, dataset, or feature dependency. It uses the `bun` package manager to manage JS/TS dependencies.

**Indicator Redundancy (VIF Argument):**
No new indicators are being added in this change. Thus, variance inflation factor (VIF) pruning or multicollinearity checks are not applicable.

**Backtest Impact:**
Since this change is strictly confined to Layer 6 (Presentation) and only reads pre-computed data from SQLite, there is **zero effect** on the Sharpe ratio or maximum drawdown of the system. Walk-forward optimization (WFO) and strategy backtests run entirely independently in the Python layers.

## Capabilities

### New Capabilities
- `lttd-api`: Exposes REST endpoints (latest, history, health) using Hono v4 to serve Daily LTTD rows from the SQLite database.

### Modified Capabilities

## Impact

- **Affected Code:** Creates new files under the `backend/` directory, primarily `backend/index.ts`.
- **APIs:** Introduces internal `/api/*` endpoints for the frontend SPA.
- **Dependencies:** Uses Bun as the package manager, adding `hono` v4 as the core web framework.
- **Systems:** Provides the data bridge between the SQLite WAL database and the React 18 frontend.
