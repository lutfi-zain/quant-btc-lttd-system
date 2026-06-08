## ADDED Requirements

### Requirement: Price and Final Score Charting
The `price-charting` capability must use TradingView Lightweight Charts to render BTC price action alongside the LTTD Final Score at the daily level.

#### Scenario: Rendering Price and Signal without Lookahead Bias
- **GIVEN** the API client has fetched historical OHLCV data and LTTD Final Scores
- **WHEN** the user views the chart at the daily level
- **THEN** the BTC price series MUST be rendered as a candlestick chart
- **AND** the LTTD Final Score MUST be rendered as an overlay or sub-chart, strictly aligned by the `data_as_of` timestamp to visually confirm the absence of Lookahead Bias

### Requirement: Plotting Feature Components
The chart must allow researchers to overlay the PCA Orthogonalization components to verify feature stability over the target epoch.

#### Scenario: Inspecting PCA Components
- **GIVEN** the chart is rendering the historical daily execution state
- **WHEN** the user toggles the PCA components view
- **THEN** the first three principal components MUST be plotted alongside the price to enable visual verification of signal variance over the 120–350 day OU Half-Life epoch (Cross-reference: See `pi_final_research_lttd_01.md` Section on Critical Research Findings regarding the OU half-life expansion and PCA multicollinearity).

## Non-Goals
- Developing a custom charting library from scratch.
- Visualizing every single raw indicator concurrently; the chart focuses on the price, Final Score, and PCA components to avoid visual clutter and enforce orthogonalization principles.
