## 1. Create `backfill_gap.py` Script

- [x] 1.1 Create `backfill_gap.py` at project root with the following structure:
  - Import `LTTDPipeline`, `DataStaleException`, database utilities
  - Accept `--non-interactive` flag (for API-triggered mode, skips confirmation prompts)
  - Implement `detect_gap()` function: query `SELECT MAX(date) FROM daily_lttd` → compute missing date range
  - Implement `check_valuation_api()` function: GET `http://localhost:5173/api/composite` with 3s timeout → return True/False
  - Implement `main()` orchestration:
    1. Call `detect_gap()` → handle empty DB (exit 1) and up-to-date DB (exit 0) cases
    2. Call `check_valuation_api()` → warn if down, prompt for confirmation in interactive mode
    3. Warn if gap > 90 days, prompt for confirmation in interactive mode
    4. Loop through missing dates chronologically, call `LTTDPipeline().run_daily(target_date)` for each
    5. Catch per-day errors (including `DataStaleException`), log, and continue
    6. Print per-day progress: `[{i}/{total}] {date}: {regime} (Score: {score:.4f}, Exposure: {exposure:.1f})`
    7. Print final summary: successful/failed counts and list of failed dates

- [x] 1.2 Verify `backfill_gap.py` handles the edge cases:
  - Empty database → prints error and exits with code 1
  - Database already up to date → prints message and exits with code 0
  - Gap of exactly 1 day → processes single date correctly
  - `--non-interactive` flag → skips all confirmation prompts (for API mode)

## 2. Add `sync_gap` Action to Backend

- [x] 2.1 Add `sync_gap` action routing in `backend/index.ts` (line ~305-316, inside the `/api/actions/run` handler):
  - Add `else if (action === "sync_gap")` block
  - Command: `["python3", "backfill_gap.py", "--non-interactive"]`
  - Keep existing `sync_today`, `recover_10d`, `full_repopulation` actions unchanged

## 3. Tests

- [x] 3.1 Create `tests/test_backfill_gap.py` with the following test cases:
  - `test_detect_gap_with_existing_data`: Mock DB with data up to N days ago, verify correct gap calculation
  - `test_detect_gap_empty_db`: Mock empty DB, verify returns None and correct error
  - `test_detect_gap_up_to_date`: Mock DB with today's date, verify gap_days = 0
  - `test_gap_fill_sequential_execution`: Verify dates are processed in chronological order
  - `test_gap_fill_error_recovery`: Verify pipeline continues after a single date failure

- [x] 3.2 Run `python -m pytest -xvs tests/test_backfill_gap.py` to validate all tests pass

## 4. Integration Validation

- [x] 4.1 Run `python -m pytest -xvs` to ensure no existing tests are broken (143 passed, 0 failed)
- [x] 4.2 Manually verify `python backfill_gap.py --non-interactive` runs correctly against the actual database (dry-run check with current gap)
