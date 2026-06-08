## 1. Project Initialization

- [ ] 1.1 Scaffold Hono v4 backend project in `backend/` using `bun`
- [ ] 1.2 Scaffold React 18 + Vite + TypeScript frontend project in `frontend/` using `bun`
- [ ] 1.3 Install backend dependencies (`hono`, SQLite driver) using `bun`
- [ ] 1.4 Install frontend dependencies (`lightweight-charts`) using `bun`

## 2. Backend API Implementation (Layer 6)

- [ ] 2.1 Implement SQLite WAL mode read-only connection in `backend/` for `database/lttd.db`
- [ ] 2.2 Create `GET /api/chart` endpoint returning OHLCV price and Final Score $\in [-1.0, 1.0]$
- [ ] 2.3 Create `GET /api/regime` endpoint returning daily 3-state HMM probabilities
- [ ] 2.4 Create `GET /api/diagnostics` endpoint returning Indicator Scores $\in \{-1, +1\}$, VIF, and PCA variance
- [ ] 2.5 Create `GET /api/onchain` endpoint returning BRK Series data with original timestamps

## 3. Frontend Core Infrastructure

- [ ] 3.1 Create global layout and application shell for the dashboard
- [ ] 3.2 Implement API client hooks to fetch and parse backend responses
- [ ] 3.3 Create synchronized crosshair context to align timestamps across multiple TradingView charts
- [ ] 3.4 Implement UTC-only timestamp parser to prevent local time shifting

## 4. Frontend Panel Components

- [ ] 4.1 Implement `LTTDChart` component with dual y-axis (candlestick for price, bounded axis for Final Score)
- [ ] 4.2 Implement `RegimePanel` component rendering stacked areas for Bull/Bear/Sideways and highlighting state > 0.50
- [ ] 4.3 Implement `FeatureDiagnosticsPanel` showing Indicator Scores, PCA > 85%, and red warnings for VIF > 10
- [ ] 4.4 Implement `OnChainPanel` plotting metrics with horizontal threshold lines (STH-MVRV > 2.0, STH-NUPL > 0.75)

## 5. Integration & Verification

- [ ] 5.1 Integrate all four panels into the main dashboard view
- [ ] 5.2 Verify chart crosshair synchronization across all instantiated panels
- [ ] 5.3 Test and verify UI boundary highlights (e.g., VIF > 10 warning) using mock data if DB is empty
