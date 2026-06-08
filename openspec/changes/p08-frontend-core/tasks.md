## 1. Project Initialization & Tooling

- [ ] 1.1 Scaffold React 18 + TypeScript Vite project in `frontend/` using `bun`
- [ ] 1.2 Install core dependencies: `lightweight-charts`, `@tanstack/react-query`, `tailwindcss` via `bun add`
- [ ] 1.3 Configure Tailwind CSS and setup global styling
- [ ] 1.4 Add `README.md` in `frontend/` detailing setup and `bun run dev` execution commands

## 2. API Client Layer (Layer 6 Integration)

- [ ] 2.1 Define domain TypeScript interfaces (`Regime`, `IndicatorScore`, `FinalScore`, PCA weights, OHLCV rows)
- [ ] 2.2 Implement API client functions to fetch historical and latest daily execution rows from the Hono REST API
- [ ] 2.3 Implement error handling logic to gracefully catch backend unavailability (e.g., 5xx errors)
- [ ] 2.4 Configure React Query `QueryClientProvider` at the application root for request caching

## 3. Dashboard UI Components

- [ ] 3.1 Create main Dashboard layout shell and responsive grid
- [ ] 3.2 Implement Regime Widget to visualize the current HMM-inferred state (BULL / BEAR / SIDEWAYS)
- [ ] 3.3 Implement Final Score Widget to numerically display the ensemble output [-1.0, +1.0]
- [ ] 3.4 Implement Indicator Metrics Widget to list individual causal Technical and On-Chain Indicator Scores (∈ {-1, +1})
- [ ] 3.5 Build Regime Shift Notification component to highlight transitions and display the corresponding timestamp

## 4. Price & Signal Charting

- [ ] 4.1 Create `TradingViewChart` React wrapper component for Canvas lifecycle management
- [ ] 4.2 Render BTC candlestick OHLCV price series on the primary chart pane
- [ ] 4.3 Render LTTD Final Score series on a synchronized sub-pane, strictly aligned by `stamp` (data_as_of) to verify zero Lookahead Bias
- [ ] 4.4 Implement UI toggle and series overlay for the first three PCA Orthogonalization components
- [ ] 4.5 Optimize chart rendering for long-term 800–1,200 day OU Half-Life epochs

## 5. Integration & Verification

- [ ] 5.1 Connect data hooks (`useQuery`) to populate the dashboard widgets and charting components
- [ ] 5.2 Implement structured error state UI fallbacks for when the Hono backend is offline
- [ ] 5.3 Validate metrics widget accurately displays discrete `{-1, +1}` values for all causal features
- [ ] 5.4 Test and verify multi-pane chart synchronization and responsive resize behavior
