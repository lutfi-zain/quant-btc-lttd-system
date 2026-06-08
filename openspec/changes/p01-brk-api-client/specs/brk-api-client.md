## Non-Goals
- Managing execution logic, trading sizes, or generating the Final Score (handled by Layer 4 and 5).
- Processing OHLCV price data or Technical Indicators (handled by Layer 2).
- Implementing the 3-state HMM or regime transition math (handled by Layer 1).
- Setting up or managing API keys, as the BRK API at bitview.space requires no authentication.

## ADDED Requirements

### Requirement: BRK API Historical Bulk Fetching
The client MUST fetch historical On-Chain Metrics from the BRK API `bulk` endpoint to populate data for Walk-Forward Optimization (WFO) and historical model training. This requirement applies at the daily level. Reference `pi_final_research_lttd_01.md` (Critical Research Findings #5) for utilizing historical on-chain variables.

#### Scenario: Fetching historical BRK Series for WFO
- **GIVEN** the WFO pipeline initializes and requests historical data for on-chain metrics
- **WHEN** the `brk-client` executes a bulk fetch via `GET /api/series/bulk?index=day&series=sth_mvrv,sth_nupl,sth_sopr_24h,sth_supply_in_profit&start=-N`
- **THEN** the response MUST return correctly formatted BRK Series with valid timestamps, and the length of the data array MUST match the requested `start` window without Lookahead Bias.

### Requirement: Real-Time Data Freshness Validation
The system MUST validate the BRK Stamp of the latest On-Chain Metric response to ensure no stale data enters the Ensemble Aggregation or Regime models. This requirement applies at the daily level. Reference `pi_final_research_lttd_01.md` (Critical Research Findings #4) regarding the danger of static array silence.

#### Scenario: Validating BRK Stamp for Live Execution
- **GIVEN** Layer 2 (Signal Engine) requests the latest On-Chain Metrics for daily LTTD calculation
- **WHEN** the `brk-client` fetches the latest value via `GET /api/series/{name}/day/latest`
- **THEN** the client MUST assert that the response `stamp` field is `>= current_date - timedelta(days=1)`. If the BRK Stamp is older, it MUST raise a validation exception to halt execution.

### Requirement: Dynamic Live Fetching
The system MUST strictly retrieve all On-Chain Metrics dynamically via `brk-client`, completely replacing legacy static array assignments that silently fail out-of-sample. This requirement applies at the daily level. Reference `pi_final_research_lttd_01.md` (Critical Research Findings #4).

#### Scenario: Replacing static historical arrays
- **GIVEN** an active regime classification cycle
- **WHEN** the system calculates regime filters based on `sth_nupl` and `sth_mvrv`
- **THEN** the pipeline MUST solely rely on the dynamically fetched `brk-client` values, ensuring the real-time execution outputs non-zero Indicator Scores and preserves the statistical integrity of the inputs.
