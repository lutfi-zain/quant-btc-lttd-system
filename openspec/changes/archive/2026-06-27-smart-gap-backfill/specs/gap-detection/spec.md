## ADDED Requirements

### Requirement: Detect Latest Database Date

The system must query the `daily_lttd` table to determine the most recent date for which LTTD data has been calculated and persisted.

#### Scenario: Database has existing data
- **WHEN** the `daily_lttd` table contains records with dates up to `2026-06-14`
- **THEN** the gap detection function returns `last_date = 2026-06-14` and `gap_days = (today - 2026-06-14).days`

#### Scenario: Database is empty
- **WHEN** the `daily_lttd` table contains zero records
- **THEN** the gap detection function returns `last_date = None` and the system prints an error message: "Database is empty. Run backfill_all.py first."
- **THEN** the process exits with code 1

#### Scenario: Database is up to date
- **WHEN** the `daily_lttd` table contains a record for today's date (UTC)
- **THEN** the gap detection function returns `gap_days = 0`
- **THEN** the system prints "Database is already up to date." and exits with code 0

### Requirement: Calculate Missing Date Range

Given the `last_date` from the database, the system must compute the exact list of dates that need to be backfilled.

#### Scenario: Multi-day gap
- **WHEN** `last_date = 2026-06-14` and `today = 2026-06-27` (UTC)
- **THEN** the missing date range is `[2026-06-15, 2026-06-16, ..., 2026-06-27]` — exactly 13 dates
- **THEN** the system prints "Found gap: 13 days (2026-06-15 → 2026-06-27)"

#### Scenario: Single day gap
- **WHEN** `last_date = 2026-06-26` and `today = 2026-06-27`
- **THEN** the missing date range is `[2026-06-27]` — exactly 1 date
