## Context

The `quant-btc-lttd-system` follows a strictly layered pipeline. Currently, we need to bridge Layer 5 (Execution Engine) with Layer 6 (Presentation). Layer 6 comprises a Hono API (running on Bun) that expects structured, persistent data. Layer 5 needs to immutably log the mathematically sound states of the model at any given time `t`, specifically tracking the `Final Score`, `Regime`, individual `Indicator Score`s, and regime transitions. Proper persistence guarantees reproducibility when auditing live system performance against Walk-Forward Optimization (WFO) backtests and eliminates the risk of ex-post data modifications.

## Goals / Non-Goals

**Goals:**
- Design the SQLite `lttd.db` schema configured in WAL mode for concurrent access.
- Define idempotent update logic (UPSERT) for daily writes originating from Layer 5.
- Establish strict schema constraints to enforce mathematical boundaries: `final_score` ∈ [-1.0, 1.0], `Indicator Score` ∈ {-1, 1}, and `Regime` restricted to `BULL`, `BEAR`, `SIDEWAYS`.
- Ensure execution logging respects the real-time `data_as_of` timestamp logic (using the `stamp` from the BRK API) to prevent Lookahead Bias.

**Non-Goals:**
- Implementing Layer 4 (Ensemble Aggregation) or Layer 1 (HMM).
- Developing the Layer 6 (Hono API/Frontend) endpoints.
- Defining tables for Walk-Forward Optimization (WFO) backtest tracking.
- Integrating with the actual real-time execution job scheduler.

## Decisions

1. **SQLite in WAL Mode as Datastore**
   - *Rationale:* Since Layer 5 writes daily execution updates while Layer 6 (Presentation) reads concurrently on user demand, WAL (Write-Ahead Logging) allows non-blocking read/write operations. The data volume is highly predictable and low (1 row per day for `daily_lttd`, N rows for `indicator_scores`), making SQLite perfectly optimal. This aligns with the architecture of the existing `quant-btc-valuation-system`.
   - *Alternative Considered:* PostgreSQL was rejected because the low throughput and single-instance nature of the LTTD runner do not justify the operational overhead of a networked database service.

2. **Idempotent Upserts using `ON CONFLICT`**
   - *Rationale:* To satisfy the idempotency requirement without duplicate records per day, Layer 5 will utilize SQLite's `INSERT INTO ... ON CONFLICT(date) DO UPDATE SET ...` syntax. This guarantees that if the Execution Engine is restarted or re-triggered on the same day, it gracefully overrides the existing outputs for that `date` without duplicating history.

3. **Schema-Level Constraints for Mathematical Integrity**
   - *Rationale:* To enforce cross-layer data integrity, SQLite `CHECK` constraints will be applied directly at the schema definition:
     - `daily_lttd`: `CHECK(regime IN ('BULL', 'BEAR', 'SIDEWAYS'))` and `CHECK(final_score >= -1.0 AND final_score <= 1.0)`
     - `indicator_scores`: `CHECK(score IN (-1, 1))`
   - *Alternative Considered:* Validating only in Python (Layer 5). Rejected because direct database modifications or bugs in Layer 5 would bypass bounds checks.

4. **Timestamp Integrity Mapped to BRK `stamp`**
   - *Rationale:* To prevent Lookahead Bias, the primary temporal key (`date` or `transition_date`) will be exclusively populated by the `stamp` value from the BRK API response (the confirmed historical data time), rather than `datetime.now()`. The `created_at` column will use the system execution time for auditing/debugging purposes only.

## Risks / Trade-offs

- **[Risk]** Delayed or stale BRK data causes an execution with an outdated `date`, inadvertently overwriting past days if not careful.
  - **Mitigation:** The Layer 5 write abstraction must assert that the provided `date` from the BRK payload is within an acceptable freshness window (e.g., `>= yesterday`) before executing the upsert transaction.
- **[Risk]** Schema migrations for future indicators breaking Layer 6 APIs.
  - **Mitigation:** The `indicator_scores` table uses a narrow schema (`date`, `indicator_name`, `score`). New indicators from the Signal Engine can be added without `ALTER TABLE` operations, as they are simply appended as new row entries with a new `indicator_name`.
