# gap-backfill

## Purpose
TBD - Handles sequential pipeline execution for missing dates and related health checks.

## Requirements

### Requirement: Sequential Pipeline Execution for Missing Dates

The system must run `LTTDPipeline.run_daily(target_date)` for each missing date in chronological order (oldest first), using the default `xgboost` ensemble mode.

#### Scenario: Successful gap fill
- **WHEN** the missing date range is `[2026-06-15, ..., 2026-06-27]` (13 dates)
- **THEN** `LTTDPipeline.run_daily()` is called 13 times in chronological order
- **THEN** each call persists a `daily_lttd` record, `indicator_scores`, and `pca_components` to the database
- **THEN** the sizing hysteresis state (`prev_exposure`) chains correctly because each day reads from the previous day's committed record

#### Scenario: Per-day progress reporting
- **WHEN** processing date `2026-06-20` (day 6 of 13)
- **THEN** stdout prints: `[6/13] 2026-06-20: BULL (Score: 0.7234, Exposure: 1.0)`
- **THEN** the output format is: `[{current}/{total}] {date}: {regime} (Score: {final_score:.4f}, Exposure: {target_exposure:.1f})`

#### Scenario: Single date fails but others succeed
- **WHEN** `run_daily(2026-06-18)` raises an exception (e.g., API timeout)
- **THEN** the error is logged: `[4/13] 2026-06-18: ERROR - Connection timed out`
- **THEN** execution continues to `2026-06-19` and subsequent dates
- **THEN** the final summary shows: `Completed: 12/13 successful, 1 failed`
- **THEN** the failed dates are listed in the summary

#### Scenario: DataStaleException handling
- **WHEN** `run_daily()` raises `DataStaleException` (BRK data not fresh enough)
- **THEN** the error is logged but does NOT halt the entire gap-fill
- **THEN** the affected date is marked as "skipped (stale data)" in the summary

### Requirement: Valuation API Health Check

Before starting gap-fill, the system must verify that `quant-btc-valuation-system` is reachable to prevent silently disabled circuit breakers.

#### Scenario: Valuation API is running
- **WHEN** `GET http://localhost:5173/api/composite` returns HTTP 200
- **THEN** gap-fill proceeds normally

#### Scenario: Valuation API is down
- **WHEN** `GET http://localhost:5173/api/composite` fails (connection refused / timeout)
- **THEN** the system prints a WARNING: "⚠️ quant-btc-valuation-system is not running. Circuit breaker will be disabled (composite defaults to 0.0)."
- **THEN** the system prints: "Continue anyway? (y/N)" for CLI mode
- **THEN** for API mode (triggered via backend), it proceeds with the warning logged (no interactive prompt)

### Requirement: Safety Limit for Large Gaps

#### Scenario: Gap exceeds 90 days
- **WHEN** the detected gap is > 90 days
- **THEN** the system prints: "⚠️ Gap is {N} days (> 90). For large gaps, consider running backfill_all.py instead."
- **THEN** the system prints: "Continue anyway? (y/N)" for CLI mode
- **THEN** for API mode, it proceeds with a warning in the output
