## Why

The quantitative LTTD system requires a persistent, low-latency storage mechanism to record the outputs of the Ensemble Aggregation and Regime Detection layers. Scaffolding the database schema ensures that daily historical `Final Score`s, `Indicator Score`s, and inferred `Regime` states (Bull/Bear/Sideways) are immutably stored for the Presentation Layer to consume. From a statistical perspective, this ensures the precise mathematical state of the live system at time `t` is recorded, eliminating ex-post data modifications and guaranteeing exact reproducibility when auditing live performance against WFO (Walk-Forward Optimization) backtests.

## What Changes

- Scaffold a local SQLite database configured in WAL mode at `database/lttd.db` for high-concurrency read/write operations.
- Define the core `daily_lttd` table schema to store timestamps, inferred `Regime` state, and the `Final Score` ∈ [-1.0, +1.0].
- Define the schema for storing individual causal `Indicator Score`s ∈ {-1, +1} to track component contributions over time.
- Define the schema for logging `Regime` transitions along with their posterior probabilities and triggering metrics.
- Establish write abstractions in Layer 5 (Execution Engine) to persist the ensemble outputs.

## Capabilities

### New Capabilities
- `db-schema`: Defines the SQLite database structure, WAL mode initialization, and table schemas (`daily_lttd`, regime transitions, indicator scores) for persistent storage.
- `execution-persistence`: Outlines the requirements for Layer 5 (Execution Engine) to write the `Final Score`, `Regime` state, and `Indicator Score`s idempotently to the database.

### Modified Capabilities

## Impact

- **Affected Layers:** Layer 5 (Execution Engine) for writing daily execution records, and Layer 6 (Presentation) for reading data to serve the Hono v4 API.
- **Backtest Impact:** No direct quantitative impact on Sharpe ratio or max drawdown, as this is purely an infrastructural change. However, it provides the fundamental storage necessary for reproducible WFO backtest evaluation and causal logging.
- **Data Dependencies:** Introduces a new local file dependency (`database/lttd.db`). No new external API dependencies are introduced in this phase.
- **VIF / Indicators:** This change does not introduce any new technical indicators or on-chain metrics; it strictly scaffolds the persistence layer for existing layers.
