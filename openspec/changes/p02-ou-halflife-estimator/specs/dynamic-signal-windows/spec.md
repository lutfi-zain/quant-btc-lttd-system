## ADDED Requirements

### Requirement: Dynamic Causal Filter Adjustment
The Signal Engine (Layer 2) SHALL dynamically adjust the historical context window size of its Causal Filters based on the current daily OU Half-Life. This applies at the daily level.

#### Scenario: OU Half-Life fluctuation adjusts filter lookback
- **GIVEN** an active Causal Filter processing daily market data
- **WHEN** a newly calibrated OU Half-Life value is provided by Layer 3
- **THEN** all instances of Causal Filter MUST resize their maximum lookback window to match the current OU Half-Life integer value
- **THEN** the window size MUST remain strictly within the [120, 350] day range

### Requirement: Zero Lookahead Bias Enforcement
The dynamic resizing of context windows MUST rely exclusively on past data and MUST NOT introduce any future data points. This applies at the bar level.

#### Scenario: Window expansion during calculation
- **GIVEN** a Causal Filter updating its internal state for time `t`
- **WHEN** the OU Half-Life increases and the Causal Filter window expands
- **THEN** the filter MUST ONLY include additional historical lags `source[t-k]`
- **THEN** the system MUST pass the `test_no_lookahead()` unit test confirming no future bars influence the current value

### Requirement: Indicator Independence
The modulation of Causal Filter windows by the OU Half-Life MUST NOT introduce multicollinearity among the Technical Indicators. This applies at the regime level.

#### Scenario: VIF Check post-adjustment
- **GIVEN** a computed matrix of Technical Indicators using dynamically adjusted windows
- **WHEN** the Ensemble Aggregation prepares the indicator matrix for PCA Orthogonalization
- **THEN** the dynamically adjusted Technical Indicators MUST NOT exceed a VIF threshold of 10
- **THEN** if redundancy is found, the system SHOULD utilize Pratt's Measure to prune redundant indicators
- **THEN** the OU Half-Life itself MUST have a VIF of 0 since it is excluded from the directional feature matrix

### Requirement: On-Chain Metric Independence
The dynamic window resizing SHALL apply exclusively to Technical Indicators and SHALL NOT affect On-Chain Metric lookbacks. This applies at the regime level.

#### Scenario: BRK API data ingestion
- **GIVEN** the system is fetching a BRK Series from the bitview.space API
- **WHEN** verifying the freshness of the data using the BRK Stamp
- **THEN** the structural timescales (e.g., 800-1,200 days) for On-Chain Metrics MUST remain independent of the current OU Half-Life

### Non-Goals
- Applying symmetric or centered windowing techniques (like non-causal Savitzky-Golay) during resizing.
- Modifying the Regime detection parameters (HMM layer), as it operates independently on returns and volatility.
