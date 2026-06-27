## Context

Currently, three backfill modes exist:

| Mode | Script | Behavior |
|---|---|---|
| **Sync Today** | `run_pipeline.py` | Runs `LTTDPipeline.run_daily()` for today only |
| **Recover 10d** | `backfill.py` | Hardcoded loop: `range(10, -1, -1)` — always 10 days back |
| **Full Repopulation** | `backfill_all.py` | Deletes ALL data, recalculates from 2016 using its own standalone pipeline (not `LTTDPipeline`) |

The problem: when the gap exceeds 10 days, users have no efficient option. `backfill.py` misses older dates, and `backfill_all.py` wastes 30+ minutes recalculating years of already-correct data.

### ML Model Architecture (No Retraining Needed)

The `LTTDPipeline.run_daily(target_date)` method already handles all model training internally per each call:
- **HMM**: Trained on a 3-year sliding window of closing prices ending at `target_date` (line 130 in `src/pipeline.py`)
- **Ensemble (XGBoost/Lasso/PCA)**: Fitted on the same 3-year window with 14-day purge gap (line 191)
- **Feature Matrix**: Built from all data up to `target_date` (line 121)
- **Sizing**: Reads `prev_exposure` and state counters from the database via `ExecutionEngine` (lines 237-240)

Each `run_daily()` call is self-contained — it trains the model for that specific date using only prior data, then persists results. **No pre-trained model checkpoint exists that would need updating.** Gap-filling is simply a sequential loop of `run_daily()` calls.

## Goals / Non-Goals

**Goals:**
- Detect the actual data gap by querying `MAX(date)` from `daily_lttd` table
- Fill exactly the missing date range (last_date + 1 day → today)
- Reuse `LTTDPipeline.run_daily()` for each date (proven, tested code path)
- Add `sync_gap` action to backend API for frontend triggering
- Provide per-day progress output (for live feedback in UI)
- Handle edge cases: empty database, database up-to-date, partially failed days

**Non-Goals:**
- Parallel execution of gap days (sizing depends on sequential `prev_exposure` state)
- Optimizing `backfill_all.py` performance (separate concern)
- Adding a frontend UI for the Sync Gap button (already has action framework — just wire the new action)
- Changing any indicator, ensemble, or sizing logic

## Decisions

### D1: Use `LTTDPipeline` (not the standalone `backfill_all.py` approach)

`backfill_all.py` has its own standalone pipeline with parallel execution (ThreadPoolExecutor) and separate model fitting. It pre-computes the entire feature matrix and processes days in parallel, then applies sequential sizing post-hoc.

For gap-filling, we use `LTTDPipeline.run_daily()` instead because:
1. **Sequential correctness**: The sizing hysteresis (binary 0/1 with `prev_exposure`) depends on the previous day's DB record being committed before the next day runs
2. **Proven code path**: `run_daily()` is the production pipeline; gap-fill should use the same path
3. **Simpler implementation**: No need to replicate the parallel-then-sequential approach from `backfill_all.py`
4. **Performance is acceptable**: For a typical gap (1-30 days), sequential `run_daily()` takes ~5-30 seconds per day (API fetch + HMM train + ensemble fit). A 30-day gap fills in ~5-15 minutes.

### D2: Gap detection via `MAX(date)` query

Query the `daily_lttd` table for the most recent date. Compute the gap as `today - max_date`. If `max_date == today`, report "already up to date" and exit.

### D3: Sequential execution order

Process dates from oldest to newest (chronological). This ensures:
- Each day's HMM training window includes the correct prior data
- The sizing engine reads the correct `prev_exposure` from the previous day (just inserted)
- Regime transition logging chains correctly

### D4: Ensemble mode consistency

Use the **default `LTTDPipeline` ensemble mode** (`xgboost`) — same as `run_pipeline.py`. This differs from `backfill_all.py` which uses `L1LassoEnsemble` directly, but consistency with the live pipeline is more important for gap-filling recent dates.

### D5: Error handling — skip and continue

If a specific date fails (e.g., API timeout, data stale), log the error and continue to the next date. Report a summary at the end showing successful/failed dates. This prevents a single transient failure from blocking the entire gap-fill.

## Risks / Trade-offs

| Risk | Severity | Mitigation |
|---|---|---|
| `quant-btc-valuation-system` not running → circuit breaker defaults to disabled (composite=0.0) | **High** | Check API health at startup. Warn user if down. Do NOT proceed without explicit flag. |
| BRK API rate limiting for many sequential requests | Low | BRK has no documented rate limit for daily endpoints. Each `run_daily()` makes ~4 API calls. For 30-day gap = ~120 calls total — well within any reasonable limit. |
| Long gap (100+ days) takes 30+ minutes | Medium | Provide clear progress output. Consider a `--max-days` safety limit (default: 90). Beyond that, suggest `backfill_all.py`. |
| Sequential execution slower than parallel `backfill_all.py` | Accepted | Correctness over speed for operational gap-fill. `backfill_all.py` remains available for full historical reconstruction. |
| Gap in the middle of existing data (not just at the tail) | Low | `MAX(date)` approach only detects tail gaps. Interior gaps require manual investigation. This is acceptable for the common use case (system was offline for N days). |
