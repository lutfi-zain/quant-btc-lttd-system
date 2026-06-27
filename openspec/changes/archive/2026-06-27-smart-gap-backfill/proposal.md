## Why

The current `backfill.py` script is hardcoded to process only the **last 10 days** regardless of the actual data gap in the database. When the system has been offline for more than 10 days (e.g., latest DB data is June 14 but today is June 27), users must either:

1. Run `backfill.py` multiple times manually (covering only 10 days each), or
2. Run `backfill_all.py` which destroys all existing data and recalculates from 2016 — a process that takes 30+ minutes.

Neither approach is acceptable. The system needs a "Sync Gap" mode that automatically detects the last available date in the database and fills only the missing days.

**Key architectural question answered: No ML retraining required.** The `LTTDPipeline.run_daily()` already handles per-day model fitting correctly — it trains a 3-year sliding window HMM + ensemble for each target date using only prior data. Gap filling simply calls `run_daily()` sequentially for each missing date. The sizing hysteresis (binary 0/1 exposure) is also stateful via the database — `ExecutionEngine.run()` reads `prev_exposure`, `days_since_exit`, and `days_in_position` from the last DB record, so sequential gap-fill naturally chains exposure state correctly.

## What Changes

1. **New `sync_gap` action in the backend** (`POST /api/actions/run` with `action: "sync_gap"`) that invokes a gap-aware backfill script.
2. **New `backfill_gap.py` script** at root level that:
   - Queries the database for the latest `date` in `daily_lttd`
   - Calculates the gap between that date and today
   - Runs `LTTDPipeline.run_daily()` sequentially for each missing date
   - Reports progress per-day
3. **Frontend "Sync Gap" button** updated to call the new `sync_gap` action (currently calls `recover_10d` which runs the hardcoded 10-day `backfill.py`).

## Capabilities

### New Capabilities
- `gap-detection`: Automatic detection of the latest date in the database and calculation of missing date range
- `gap-backfill`: Sequential pipeline execution for each missing date, with progress reporting and error handling per-day

### Modified Capabilities
- `backfill-actions`: The backend `/api/actions/run` endpoint gains a new `sync_gap` action type

## Impact

- **Affected code:**
  - New file: `backfill_gap.py` (root level)
  - Modified: `backend/index.ts` (add `sync_gap` action routing)
  - Modified: Frontend sync button (if present — currently no UI exists, may need to add)
- **Layer boundaries:** Only Layer 5 (Execution) is touched for gap detection. The pipeline orchestration (`LTTDPipeline`) is called as-is.
- **Dependencies:** No new dependencies. Uses existing `LTTDPipeline`, `SQLiteCache`, and `ExecutionEngine`.
- **Backtest Impact:** None — this is an operational/infrastructure change, not a model change. No indicator or ensemble logic is altered.
- **Risk:** Low. The `run_daily()` path is already battle-tested for single-day execution. Gap fill is just a loop over that path.
