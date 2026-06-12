## Context

<!-- Background and current state -->
This design document addresses the technical details for integrating dynamic lookbacks, fixing BRK series-specific timestamps, and securing cached data writes from primary key constraint violations:
1. **Dynamic Lookbacks:** `KalmanRSI` and `AdvancedStochastic` accept the parameters but bypass them in their compute steps.
2. **BRK Data Sync Stamps:** The BRK client relies on a global sync check instead of checking the series data directly, which can hide stale endpoints.
3. **Database Caching:** `save_dataframe` uses pandas `to_sql(if_exists="append")`, which causes a crash if any row already exists.

## Goals / Non-Goals

**Goals:**
- Ensure indicators adapt dynamically to the market regime.
- Guarantee exact on-chain staleness metrics based on individual series stamps.
- Make database writes idempotent.

**Non-Goals:**
- Removing indicators or changing their mathematical formulas.

## Decisions

### Decision 1: Resolve Indicator Dynamic Lookback Loops
- **Choice:** Update `KalmanRSI.compute()` and `AdvancedStochastic.compute()` to resolve the lookback list via `self._resolve_lookback()`. For `AdvancedStochastic`, scale the rolling window bounds dynamically. For `KalmanRSI`, scale the rolling normalizer bounds.
- **Rationale:** Aligns implementation with the parent indicator classes and ensures regime compliance.

### Decision 2: Query Individual BRK Series Details
- **Choice:** Use the client's direct query endpoints or inspect the last record in the bulk responses to identify the exact series update timestamp.
- **Rationale:** The global sync status is a general metadata field that does not represent individual table states.

### Decision 3: Idempotent DB Upsert Strategy
- **Choice:** Modify the database `save_dataframe` query to handle duplicates (e.g. filter out existing indices prior to writing, or execute a custom SQL upsert query using `sqlite3`).
- **Rationale:** A pre-check filter or standard SQL `INSERT OR REPLACE` query prevents database locking and handles duplicate appends elegantly.

## Risks / Trade-offs

- **[Risk]** Dynamic lookbacks might make indicator loops slower if calculated row-by-row.
  - **Mitigation:** Vectorize lookback applications where possible, or optimize rolling computations using numpy.
