# causal-price-filtering Specification

## Purpose
TBD - created by archiving change p01-ohlcv-data-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Chronological Order Validation
The system SHALL validate that all incoming OHLCV data is strictly sorted chronologically (ascending by date) before any processing. This applies at the daily level.

#### Scenario: Rejecting unsorted or reverse-chronological data
- **GIVEN** an OHLCV DataFrame
- **WHEN** the DataFrame is not sorted in chronological order
- **THEN** the pipeline raises a `ValueError` indicating a chronological ordering failure.

### Requirement: Causal Window Enforcement
The system SHALL exclusively use causal forward-filtering logic (e.g., `shift(1)` for lags). The system MUST NOT apply symmetric window filters (like default Savitzky-Golay) that introduce lookahead bias. This requirement prevents Lookahead Bias, enforcing the constraint found in pi_final_research_lttd_01.md. This applies at the bar level.

#### Scenario: Causal filtering without lookahead bias
- **GIVEN** a price filter function configured for the OHLCV pipeline
- **WHEN** it processes the OHLCV DataFrame up to time `t`, and then re-processes the DataFrame with future bars `t+1..t+N` appended
- **THEN** the filtered output at time `t` remains identical in both cases (verifiable via a `test_no_lookahead` unit test).

