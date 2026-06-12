# brk-ingestion-sync Specification

## Purpose
TBD - created by archiving change p07-e2e-pipeline-runner. Update Purpose after archive.
## Requirements
### Requirement: Bulk On-Chain Metric Fetching
The system SHALL systematically fetch required On-Chain Metrics (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`) using the `brk-client` bulk endpoint (`GET /api/series/bulk`) at the **daily level**.

#### Scenario: Successful bulk data sync
- **GIVEN** the orchestrator initiates a daily execution run
- **WHEN** the data ingestion phase executes
- **THEN** the system SHALL receive a JSON array from `bitview.space` mapping exactly to the 4 specified series names with a response size `> 0`.

### Requirement: Strict Data Freshness and Timestamp Validation
The system SHALL validate the `stamp` field from the BRK API response and use it as the definitive `data_as_of` record at the **daily level** to eliminate Lookahead Bias.

#### Scenario: Validating the BRK Stamp
- **GIVEN** a new daily On-Chain Metric payload is received
- **WHEN** aligning the metric with the OHLCV daily price bar
- **THEN** the system SHALL assert that `brk_feed.stamp >= current_date - timedelta(days=1)`, and if false, throw a `DataStaleException` preventing the Execution Engine from generating a new LTTD position.

### Requirement: Minimum Data Lookback Constraints
The system SHALL guarantee that sufficient historical context is pulled for On-Chain Metric filtering at the **regime level**.

#### Scenario: 1,200-day minimum lookback retrieval
- **GIVEN** the daily orchestration pipeline is cold-started
- **WHEN** the brk-ingestion-sync initializes the dataset for historical rolling statistics
- **THEN** it SHALL request and store at least the last 1,200 days of historical data to satisfy the Glassnode feature discovery window for optimal BTC uptrend detection, defined in `pi_final_research_lttd_01.md`.

### Requirement: Series-Specific BRK Timestamping
Enforce that on-chain data timestamps match the exact update time of the fetched series.

#### Scenario: Stale Series Detection
- **GIVEN** a requested BRK series name.
- **WHEN** fetching the latest value from bitview.space.
- **THEN** the returned stamp SHALL reflect when that specific series was last updated, not the global index synchronization time.
