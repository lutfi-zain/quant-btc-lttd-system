# Delta Specifications: Data and Ingestion Safeguards

## ADDED Requirements

### Requirement: Idempotent OHLCV Caching
Enforce that caching of OHLCV data is idempotent and does not fail when duplicate records are written.

#### Scenario: Duplicate OHLCV Append
- **GIVEN** a cache SQLite database with an existing OHLCV table.
- **WHEN** the ingestion service appends OHLCV records containing timestamps that already exist in the database.
- **THEN** the database SHALL update the existing rows or ignore the duplicate timestamps.
- **AND** the write operation SHALL complete successfully without raising primary key or integrity constraints.

---

### Requirement: Adaptive Indicator Lookback
Enforce that Kalman RSI and Advanced Stochastic indicators adjust their parameters based on resolved dynamic lookbacks.

#### Scenario: Volatility-Responsive Window Calibration
- **GIVEN** a DataFrame of OHLCV prices and a Series of dynamically resolved lookbacks.
- **WHEN** computing indicator scores.
- **THEN** the indicator calculations SHALL utilize the daily lookback values resolved by the CausalFilter base class.

---

### Requirement: Series-Specific BRK Timestamping
Enforce that on-chain data timestamps match the exact update time of the fetched series.

#### Scenario: Stale Series Detection
- **GIVEN** a requested BRK series name.
- **WHEN** fetching the latest value from bitview.space.
- **THEN** the returned stamp SHALL reflect when that specific series was last updated, not the global index synchronization time.

---

## Non-Goals
- Altering the primary Glassnode API endpoints or introducing paid third-party data providers.
- Changing the database file format from SQLite.
