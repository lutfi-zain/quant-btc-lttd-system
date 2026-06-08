## Context

The quant-btc-lttd-system implements a 6-layer pipeline to determine Bitcoin's Long-Term Trend Direction (LTTD). Layers 1 through 5 handle the quantitative modeling—including HMM regime detection, causal signal generation, PCA orthogonalization/VIF pruning, and ensemble aggregation. To effectively monitor, validate, and debug this pipeline without relying purely on backend logs, we need a robust Presentation layer (Layer 6). The current change focuses on building a React 18 SPA to visualize the statistical and mathematical properties of the system, including HMM regime probabilities, orthogonalized indicators, on-chain metrics from the BRK feed, and the final ensemble output score.

## Goals / Non-Goals

**Goals:**
- Create a modular React 18 Single Page Application (SPA) using Vite and TypeScript.
- Build a main dashboard utilizing TradingView Lightweight Charts to overlay the LTTD Final Score ($\in [-1.0, +1.0]$) against BTC OHLCV price data.
- Develop a **Regime Panel** to visualize the 3-state HMM posterior probabilities (Bull, Bear, Sideways) over time.
- Develop a **Feature Diagnostics Panel** to display PCA component weights and VIF metrics, validating the absence of multicollinearity ($VIF \le 10$).
- Develop an **On-Chain Metrics Panel** plotting normalized BRK feeds (STH-MVRV, STH-NUPL, STH-SOPR) alongside critical threshold boundaries.
- Ensure all dependencies are installed and managed using `bun`.

**Non-Goals:**
- Modifying any quantitative logic, WFO pipelines, or models in Layers 1-5.
- Introducing new technical indicators or on-chain metrics.
- Fetching data directly from SQLite or `bitview.space` from the frontend (the frontend will exclusively consume endpoints provided by the Layer 6 Hono backend).
- Complex user authentication or multi-tenant user management.

## Decisions

1. **Frontend Stack: React 18 + Vite + TypeScript**
   - *Rationale:* React provides the component-driven architecture needed for separate independent panels. Vite ensures fast builds and Hot Module Replacement (HMR). TypeScript is critical to strongly type the complex mathematical and statistical payloads returned by the API (e.g., distinguishing between indicator scores $\in \{-1, 1\}$ and final scores $\in [-1.0, 1.0]$).
   - *Alternatives Considered:* Next.js was considered but rejected because SSR adds unnecessary complexity for a private, data-dense quantitative dashboard.

2. **Package Manager: `bun`**
   - *Rationale:* Aligns with the strict user instruction to use `bun` as the default package manager for all JS/TS projects.

3. **Charting Library: TradingView Lightweight Charts**
   - *Rationale:* Optimized specifically for financial time-series data using HTML5 Canvas. It provides out-of-the-box support for candlestick charts, synchronized crosshairs across multiple panels, and dual y-axis rendering, which is essential for overlaying bounded scores on unbounded price data.
   - *Alternatives Considered:* Chart.js and Recharts. Rejected because they lack native, highly-performant OHLCV primitives and struggle with synchronized time scales across multiple independent charts.

4. **Component Architecture & Synchronization**
   - *Rationale:* The dashboard will consist of independent components (`LTTDChart`, `RegimePanel`, `FeatureDiagnosticsPanel`, `OnChainPanel`). A centralized chart context or synchronized crosshair API will link the time scales across the components. This allows a user to hover over a specific date and simultaneously see the price, HMM regime probability, and underlying PCA components.

5. **Data Fetching Strategy**
   - *Rationale:* Native `fetch` with React hooks will be used to query the local Hono API backend. Since the quantitative data is computed daily (closing bars), real-time WebSocket streaming is unnecessary. Data will be fetched once on load, with a manual refresh trigger.

## Risks / Trade-offs

- **[Performance Degradation with Large Datasets]** $\rightarrow$ Rendering 4-5 synchronized charts with several years of daily data (~1500+ data points per series) could cause canvas lag.
  - *Mitigation:* TradingView Lightweight Charts is designed for this scale. We will instantiate charts with `handleScroll` and `handleScale` optimizations, and ensure unnecessary re-renders are prevented using React `useMemo` and `useRef` for chart instances.
- **[Time Zone & Alignment Mismatch]** $\rightarrow$ OHLCV price timestamps might misalign with BRK on-chain data `stamp` values or causal indicator outputs, leading to visual lookahead bias on the charts.
  - *Mitigation:* The frontend will strictly parse and align all data points to UTC timestamps (Midnight UTC). The UI will rely solely on the backend's unified timeline provided by the Hono API, ensuring the frontend does not perform any ad-hoc time shifting.
