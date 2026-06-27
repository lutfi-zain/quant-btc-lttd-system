# backfill-actions

## Purpose
TBD - Handles backend action routing for gap backfills.

## Requirements

### Requirement: Backend Action Routing for sync_gap

The backend `/api/actions/run` endpoint must accept a new `sync_gap` action that invokes the gap-aware backfill script.

#### Scenario: sync_gap action invoked
- **WHEN** a POST request to `/api/actions/run` with body `{"action": "sync_gap"}` is received
- **THEN** the backend spawns `python3 backfill_gap.py` (with `--non-interactive` flag for API mode)
- **THEN** the response includes `{"success": true/false, "output": "...", "error_output": "..."}`

#### Scenario: Existing actions unaffected
- **WHEN** a POST request to `/api/actions/run` with `action: "sync_today"` is received
- **THEN** it still runs `python3 run_pipeline.py` (unchanged behavior)

#### Scenario: recover_10d action preserved
- **WHEN** a POST request to `/api/actions/run` with `action: "recover_10d"` is received
- **THEN** it still runs `python3 backfill.py` (unchanged behavior — the old 10-day script is preserved for backward compatibility)
