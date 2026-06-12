# ohlcv-ingestion Specification

## Purpose
TBD - created by archiving change p01-ohlcv-data-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Configurable Exchange Data Source
The system SHALL fetch daily BTC OHLCV data via an ExchangeAdapter abstract base class, utilizing the `BTC_DATA_SOURCE` and `EXCHANGE_API_KEY` environment variables. This applies at the daily level.

#### Scenario: Successful data ingestion from configured source
- **GIVEN** a running system with valid `BTC_DATA_SOURCE` and `EXCHANGE_API_KEY` environment variables
- **WHEN** the `ohlcv-ingestion` pipeline is executed
- **THEN** it instantiates the correct ExchangeAdapter and successfully fetches a daily OHLCV dataset.

### Requirement: Standardized Output Format
The system SHALL standardize the fetched OHLCV data into a time-indexed `pandas.DataFrame`. The index MUST enforce a 00:00:00 UTC boundary. This applies at the daily level.

#### Scenario: Data standardization to UTC boundary
- **GIVEN** raw OHLCV data retrieved from the exchange adapter with arbitrary timestamps
- **WHEN** the data is processed by the ingestion pipeline
- **THEN** the returned pandas DataFrame has a `DatetimeIndex` set to exactly 00:00:00 UTC for each bar.

### Requirement: Local Caching of Historical Data
The system SHALL cache historical OHLCV data locally in SQLite WAL mode (`database/lttd.db`) and only fetch the delta (new bars) on subsequent runs to reduce API load. This applies at the daily level.

#### Scenario: Fetching delta data with existing cache
- **GIVEN** the local SQLite database contains historical OHLCV data up to time `t-1`
- **WHEN** the ingestion pipeline is triggered
- **THEN** the pipeline queries the exchange adapter ONLY for bars from time `t` to the present.

### Requirement: Index Continuity and Missing Data Handling
The system SHALL enforce strict index continuity. Missing daily bars MUST be forward-filled (`ffill()`) for `Close`, `High`, `Low`, and `Open` prices, and `Volume` MUST be set to `0.0`. This applies at the daily level.

#### Scenario: Handling a missing trading day
- **GIVEN** an exchange outage results in a missing daily OHLCV bar in the fetched data
- **WHEN** the index continuity validation is applied
- **THEN** the pipeline outputs a continuous DatetimeIndex, the missing price fields equal the previous day's close price, and the volume is exactly 0.0.

### Requirement: Idempotent OHLCV Caching
Enforce that caching of OHLCV data is idempotent and does not fail when duplicate records are written.

#### Scenario: Duplicate OHLCV Append
- **GIVEN** a cache SQLite database with an existing OHLCV table.
- **WHEN** the ingestion service appends OHLCV records containing timestamps that already exist in the database.
- **THEN** the database SHALL update the existing rows or ignore the duplicate timestamps.
- **AND** the write operation SHALL complete successfully without raising primary key or integrity constraints.
