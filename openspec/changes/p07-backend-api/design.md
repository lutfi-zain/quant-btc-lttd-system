## Context

The quantitative LTTD (Long-Term Trend Direction) trading system operates on a strict 6-layer architecture. Layers 1 through 5 handle statistically-grounded computations (HMM regime detection, PCA orthogonalization, VIF pruning, and Lasso Logistic Regression ensemble), culminating in the Execution Engine (Layer 5) writing daily position data and final scores to a local SQLite database (`database/lttd.db`) configured in WAL mode.

Currently, the Layer 6 Presentation tier is missing its backend API. The system requires a data bridge to expose the computed macro directional bias (Final Score ∈ [-1.0, +1.0] and Regime) to the React 18 frontend Single Page Application (SPA). The API must be completely decoupled from the Python execution engine to ensure read operations do not interfere with live trading logic or introduce latency to the core ML computations.

## Goals / Non-Goals

**Goals:**
- Provide a fast, lightweight REST API using Hono v4 on the Bun runtime.
- Securely and safely read pre-computed daily LTTD records from `database/lttd.db` without locking the Python writer.
- Serve standard endpoints (`/api/health`, `/api/lttd/latest`, `/api/lttd/history`) formatted correctly for TradingView Lightweight Charts.
- Adhere strictly to the domain ubiquitous language (e.g., `final_score`, `regime`, `indicator_score`).

**Non-Goals:**
- Performing any mathematical computations, PCA orthogonalization, or regime classification within the JS/TS backend.
- Modifying, inserting, or deleting rows in the SQLite database.
- Integrating directly with the BRK/bitview.space API for on-chain metrics (this is strictly handled by Python in Layer 2).

## Decisions

**1. Runtime and Web Framework: Bun + Hono v4**
- **Rationale**: Bun provides an extremely fast JavaScript runtime with built-in native SQLite bindings (`bun:sqlite`), removing the need for external native modules like `better-sqlite3` or node-gyp builds. Hono v4 is an ultra-fast, lightweight web framework that pairs perfectly with Bun to serve JSON APIs with minimal overhead.
- **Alternatives Considered**: 
  - *FastAPI (Python)*: While convenient to stay in the Python ecosystem, it risks bleeding Layer 1-5 quantitative logic into the presentation layer. Separating the API into a distinct runtime enforces the architectural boundary.
  - *Express + Node.js*: Considerably slower and requires heavier dependencies to interface with SQLite.

**2. Database Access Strategy: Read-Only Native SQLite Driver**
- **Rationale**: The Python Execution Engine (Layer 5) continuously writes daily updates to the SQLite database. To prevent `SQLITE_BUSY` errors and concurrency locks, the Bun backend will connect to `database/lttd.db` explicitly using the `readonly: true` flag. We rely on the WAL (Write-Ahead Logging) journal mode established by the Python layer to allow simultaneous readers and writers.
- **Alternatives Considered**: 
  - *Full ORM (e.g., Prisma)*: Overkill for a simple read-heavy system containing primarily one or two time-series tables (`daily_lttd`). Raw SQL via `bun:sqlite` is faster and simpler.

**3. API Payload Structure & Domain Language**
- **Rationale**: The API responses will exactly mirror the ubiquitous language established by the quantitative layers. Fields like `final_score` (float between -1.0 and 1.0) and `regime` (string: "BULL", "BEAR", or "SIDEWAYS") will be enforced. This guarantees that the frontend charts reflect the statistical reality computed by the ensemble model without arbitrary mapping layers.

## Risks / Trade-offs

- **[Risk] Database Locking/Corruption** → **Mitigation**: The system heavily relies on SQLite WAL mode. We must ensure the `bun:sqlite` connection is strictly opened in read-only mode and that the Python backend correctly initializes the database with `PRAGMA journal_mode=WAL;`.
- **[Risk] Payload Size for Time-Series History** → **Mitigation**: Since the LTTD history could span 4000+ daily records, a full fetch might eventually become large. The `/api/lttd/history` endpoint should implement optional `start` and `end` query parameters (timestamps) so the React frontend can limit the initial historical load if needed.
- **[Risk] Sync Latency** → **Mitigation**: The API only serves what is currently written in the DB. The frontend may be slightly behind real-time, but since the system measures Long-Term Trend Direction (120-350 day horizon) on daily close, microsecond latency is acceptable and irrelevant to the trading logic.

## Migration Plan

1. Initialize the Bun project in the `backend/` directory (`bun init`).
2. Install dependencies: `bun add hono`.
3. Implement `index.ts` containing the Hono app and `bun:sqlite` read-only connection logic.
4. Add basic test data (or a mock SQLite DB generator) if the Python execution layer is not yet outputting `lttd.db`.
5. Deploy using standard Bun execution (`bun run backend/index.ts`) bound to an internal port (e.g., 3000), making it available to the frontend.

## Open Questions

- Does the frontend require intermediate indicator scores (like PCA components, or VIF-pruned individual metric scores) to display in a debugging panel, or only the `final_score`, `regime`, and top contributors?
- Should we add basic rate-limiting to the Hono API, or is it purely internal/behind a reverse proxy (e.g., NGINX/Cloudflare) that handles abuse prevention?
