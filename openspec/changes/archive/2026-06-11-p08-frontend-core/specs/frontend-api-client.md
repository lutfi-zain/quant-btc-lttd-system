## ADDED Requirements

### Requirement: Fetching Execution Data
The `frontend-api-client` must retrieve historical and real-time execution rows directly from the Layer 6 Hono v4 backend at the daily level.

#### Scenario: Retrieving Daily Execution Rows
- **GIVEN** the Layer 6 backend API is running and serving data from `lttd.db`
- **WHEN** the frontend initializes or the user requests a data refresh at the daily level
- **THEN** the client MUST successfully fetch the daily execution rows via REST
- **AND** the parsed payload MUST contain the Final Score ∈ [-1.0, +1.0], Regime state, and individual Indicator Scores ∈ {-1, +1} (Cross-reference: See `pi_final_research_lttd_01.md` for mathematical proofs on ensemble signal aggregation)

### Requirement: Handling API Failures
The API client must gracefully handle backend unavailability or fetch errors.

#### Scenario: Backend Unreachable
- **GIVEN** the frontend requires data to render the dashboard
- **WHEN** the Layer 6 Hono backend is unreachable or returns a 5xx error
- **THEN** the API client MUST catch the error and present a structured error state on the UI without crashing
- **AND** the UI MUST indicate that the system state cannot be retrieved

## Non-Goals
- Polling the backend continuously at high frequency; a manual refresh or load-time fetch is sufficient for daily level data.
- Connecting directly to `database/lttd.db` or calling Python layers directly from the frontend.
