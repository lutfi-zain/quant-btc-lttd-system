# onchain-data-ingestion Specification

## Purpose
TBD - created by archiving change p03-onchain-signals. Update Purpose after archive.
## Requirements
### Requirement: Daily On-Chain Metric Ingestion
The system SHALL integrate the `brk-client` to fetch daily On-Chain Metrics (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, and `sth_supply_in_profit`) from the BRK API (`https://bitview.space`). This requirement applies at the **daily level**.

#### Scenario: Bulk fetching for Walk-Forward Optimization
- **GIVEN** the system is executing historical Walk-Forward Optimization (WFO)
- **WHEN** the `OnChainFeed` module requests historical data via the `/api/series/bulk` endpoint
- **THEN** the `brk-client` returns a structured time-series for all specified series without missing days, maintaining strict chronological order.

#### Scenario: Live inference fetching
- **GIVEN** the system is running in live execution mode for the current day
- **WHEN** the `OnChainFeed` module requests the latest value using the `/api/series/{name}/day/latest` endpoint
- **THEN** the system receives the most recent confirmed value with an intact BRK Stamp field.

### Requirement: Causal Validation and Lookahead Bias Prevention
The system SHALL strictly validate the BRK Stamp field of all on-chain data responses to prevent Lookahead Bias. Data MUST only be used if the BRK Stamp is strictly less than or equal to the current OHLCV bar's close time (or `>= current_date - timedelta(days=1)` for live execution). This applies at the **bar level**. Cross-reference: pi_final_research_lttd_01.md Section "Historical SGF Lookahead Bug".

#### Scenario: Valid timestamp alignment
- **GIVEN** a live OHLCV bar closing at day `T`
- **WHEN** the `OnChainFeed` provides an On-Chain Metric with a BRK Stamp of day `T-1` (which is `>= current_date - timedelta(days=1)`)
- **THEN** the data is merged using a Causal Filter `asof` merge, and the On-Chain Metric is confirmed causal before feeding into the Ensemble Aggregation.

#### Scenario: Stale data rejection
- **GIVEN** the BRK API has not updated and the latest available data is 4 days old
- **WHEN** the `OnChainFeed` attempts to validate the metric's BRK Stamp against the staleness threshold (max 3 days)
- **THEN** the system applies a 0.0 (neutral) signal weight for the on-chain component and falls back entirely to OHLCV Technical Indicators for the Final Score.

