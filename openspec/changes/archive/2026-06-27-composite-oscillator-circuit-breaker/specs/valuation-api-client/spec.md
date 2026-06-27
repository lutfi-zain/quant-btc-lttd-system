## ADDED Requirements

### Requirement: Valuation API Client
The system MUST implement a robust API client in Layer 2 (Data Ingestion) to fetch the daily Composite Oscillator value from the `quant-btc-valuation-system` running locally at `http://localhost:5173/api/composite`.

#### Scenario: Successful Daily Fetch
- **WHEN** the daily pipeline runs
- **THEN** it successfully fetches the JSON array from the valuation API.
- **AND** it extracts the `composite_value` for the current or most recent trading day.

#### Scenario: API Unreachable or Timeout
- **WHEN** the valuation API is down, returns a 5xx error, or times out
- **THEN** the system logs a descriptive warning.
- **AND** the system safely defaults to a neutral composite value (`0.0`) to allow the pipeline to proceed using native HMM/Momentum logic without crashing.

#### Scenario: Data Parsing
- **WHEN** the JSON response is received
- **THEN** it correctly parses the `date` and `composite_value` fields.
- **AND** it accurately handles timezones by aligning the date to the standard BTC daily close timeframe.
