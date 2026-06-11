## Context

The Bitcoin LTTD system produces quantitative signals reflecting macroeconomic directional bias (BULL / BEAR / SIDEWAYS) over 120–350 day OU half-life epochs. Currently, the system's execution and states (3-state HMM probabilities, PCA-orthogonalized feature weights, and causal indicator scores) are localized within the backend execution engine (Layer 5) and SQLite database. To guarantee observability, verify the absence of lookahead bias, and track real-time causal filter performance, a visual presentation layer (Layer 6) is necessary. The designated architecture utilizes React 18, TypeScript, and Vite, managed exclusively with the `bun` package manager.

## Goals / Non-Goals

**Goals:**
- Establish a responsive dashboard to visualize the LTTD Final Score ([-1.0, +1.0]), HMM Regime states, and causal indicator outputs (∈ {-1, +1}).
- Overlay quantitative metrics against BTC price action utilizing TradingView Lightweight Charts.
- Build a lightweight, strictly read-only presentation client that integrates seamlessly with the internal Hono v4 backend REST API.
- Support visual verification of WFO (Walk-Forward Optimization) behavior over long-term epochs.

**Non-Goals:**
- Implementing any trading execution logic or statistical computations on the client.
- Creating a public-facing, authenticated, or SSR-optimized application (this is an internal research tool).
- Modifying the SQLite schema or adjusting pipeline models (Layers 1-5).
- Supporting historical backtest execution inputs from the UI.

## Decisions

**1. Build Tooling & Package Manager: Vite + Bun**
- **Rationale**: Vite provides near-instantaneous Hot Module Replacement (HMR) and optimized builds for SPAs. `bun` is explicitly mandated by the repository rules for all JavaScript/TypeScript projects, bypassing npm or pnpm to enforce execution speed and consistency.
- **Alternatives Considered**: Create React App (deprecated, slow build times) and Next.js. Next.js was dismissed as Server-Side Rendering (SSR) is unnecessary for a static internal dashboard built heavily on client-side Canvas rendering.

**2. Charting Library: TradingView Lightweight Charts**
- **Rationale**: Highly optimized for rendering thousands of time-series financial data points without lag. It natively handles OHLCV price series and allows for synchronized multi-pane setups (e.g., Price on Pane 1, LTTD Final Score on Pane 2).
- **Alternatives Considered**: Chart.js and Recharts. Both are adequate for generic dashboards but suffer major performance degradation when panning/zooming over extensive OHLCV and indicator timelines.

**3. Data Fetching & Client State: React Query + Native Fetch**
- **Rationale**: React Query handles caching, background refetching, and async state mapping smoothly. This is critical for pulling historical execution rows from the Hono API and ensuring data freshness without building manual retry wrappers.
- **Alternatives Considered**: Redux (excessive boilerplate for purely read-only state) and native React Context (lacks request deduplication and automated caching).

**4. UI Component Library: Tailwind CSS**
- **Rationale**: Enables rapid implementation of data-dense dashboard cards (e.g., displaying current HMM regime probabilities and active features) while maintaining a clean footprint.
- **Alternatives Considered**: Material-UI (heavy bundle size and rigid styling) and standard CSS modules (slower styling iteration).

## Risks / Trade-offs

- **[Risk] High memory usage and canvas stuttering when rendering large multi-year historical datasets**
  - **Mitigation**: Default to loading the most recent epoch (e.g., 800–1,200 days) that captures the relevant structural context. If the full history is needed, implement pagination or leverage the Hono API to serve downsampled datasets for macroscopic views.
- **[Risk] Timeline misalignment between internal BRK indicators and chart plotting**
  - **Mitigation**: Ensure strict adherence to the `stamp` field in API responses (representing `data_as_of`). The X-axis standard must consistently reflect the close of the confirmed daily bar to prevent the illusion of lookahead bias on the charts.

## Migration Plan

1. Initialize the application template in the `frontend/` directory using `bun create vite`.
2. Configure TypeScript, Tailwind CSS, and install necessary dependencies (e.g., `lightweight-charts`, `react-query`).
3. Set up the API client layer pointing to local Hono endpoints (Layer 6 backend).
4. Implement the core dashboard shell layout.
5. Integrate the TradingView chart widget with multi-pane capability for Price, Regime Bands, and Final Score.
6. Verify development documentation instructs users to utilize the `bun run dev` command.

## Open Questions

- What is the preferred automatic polling interval for the Hono execution API, or will the dashboard rely entirely on manual refresh for daily-frequency data?
- Should the dashboard surface the Pratt's Measure and VIF values for current ensemble features, or strictly limit the display to the Final Score and HMM probability distributions?
- Will the Hono API provide pre-formatted OHLCV data alongside the LTTD scores, or does the frontend need to construct the composite view from separate endpoint calls?
