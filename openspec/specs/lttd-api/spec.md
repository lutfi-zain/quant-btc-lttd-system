# lttd-api Specification

## Purpose
TBD - created by archiving change p07-backend-api. Update Purpose after archive.
## Requirements
### Requirement: Backend API Health Check
The Layer 6 Presentation API SHALL expose a daily level endpoint `GET /api/health` to confirm the Hono v4 server is operational and the read-only connection to the SQLite database is established.

#### Scenario: Health check successful execution
- **GIVEN** the Hono API is running on the Bun runtime
- **WHEN** a client issues a `GET /api/health` request
- **THEN** the server SHALL respond with an HTTP 200 status
- **THEN** the response JSON payload MUST contain a boolean indicating a successful SQLite connection.

### Requirement: Latest Daily LTTD Record Retrieval
The Layer 6 Presentation API SHALL provide a daily level endpoint `GET /api/lttd/latest` that queries `database/lttd.db` to serve the most recent LTTD evaluation. It must strictly serve the Final Score and Regime without performing any mathematical transformations, referencing the pre-computed layer definitions in `pi_final_research_lttd_01.md`.

#### Scenario: Retrieving the most recent LTTD state
- **GIVEN** the Layer 5 Execution Engine has successfully persisted a new daily LTTD record
- **WHEN** a client issues a `GET /api/lttd/latest` request
- **THEN** the server SHALL respond with an HTTP 200 status
- **THEN** the JSON response SHALL contain exactly one record
- **THEN** the record MUST include the `timestamp` (data_as_of timestamp)
- **THEN** the record MUST include `final_score` such that `final_score` ∈ [-1.0, +1.0]
- **THEN** the record MUST include `regime` mapped to exactly one of: "BULL", "BEAR", or "SIDEWAYS" (the HMM-inferred state).

### Requirement: Historical LTTD Records Bulk Retrieval
The Layer 6 Presentation API SHALL provide a daily level endpoint `GET /api/lttd/history` to retrieve a time-series array of historical daily LTTD records. This ensures the React SPA can plot the historical Final Score and Regime transitions.

#### Scenario: Fetching historical LTTD time-series data
- **GIVEN** the SQLite database contains multiple historical daily LTTD records
- **WHEN** a client issues a `GET /api/lttd/history` request with valid `start` and `end` bounds
- **THEN** the server SHALL respond with an HTTP 200 status
- **THEN** the JSON response SHALL contain a time-ordered array of records
- **THEN** every returned record MUST expose a `final_score` ∈ [-1.0, +1.0] and a valid `regime` (BULL / BEAR / SIDEWAYS).

