## ADDED Requirements

### Requirement: WAL-mode SQLite database initialization
The system SHALL initialize and maintain a SQLite database at `database/lttd.db` using WAL (Write-Ahead Logging) mode to safely permit concurrent reads from Layer 6 (Presentation).

#### Scenario: First-time database creation
- **GIVEN** the system starts up
- **WHEN** the `database/lttd.db` file does not exist
- **THEN** the Execution Engine SHALL create the database, enable WAL mode, and execute the table schema migrations (e.g., creating the `daily_lttd` table)

### Requirement: Persisting daily execution state
The Execution Engine SHALL write a comprehensive record of the final system state at the close of every daily bar.

#### Scenario: Storing the daily execution row
- **GIVEN** the completion of Layer 4 (Ensemble Aggregation) and Layer 5 sizing logic
- **WHEN** a new target exposure is computed for the daily bar
- **THEN** the system SHALL insert a row into the `daily_lttd` table containing the BRK `stamp` (as `data_as_of`), the continuous `Final Score`, the categorical `Regime`, and the computed target exposure

### Requirement: Handling concurrent presentation reads
The persistence layer SHALL NOT lock the database exclusively during regular writes, ensuring the Hono v4 backend can serve the React SPA without blocking.

#### Scenario: Concurrent write and read
- **GIVEN** the Execution Engine is writing the latest daily execution row
- **WHEN** the Layer 6 Hono backend queries the `daily_lttd` table simultaneously
- **THEN** the read operation SHALL succeed without returning a SQLITE_BUSY error

## Non-Goals
- Full ORM integration (e.g., SQLAlchemy) — raw SQL or a lightweight query builder is preferred to maintain simplicity.
- Persisting high-frequency intraday metrics (only the final daily aggregation is stored).
