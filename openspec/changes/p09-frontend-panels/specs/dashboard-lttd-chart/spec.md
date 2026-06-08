## Non-Goals
- Real-time tick execution or sub-daily bar rendering.
- Strategy execution or order placement from the UI.
- Direct interaction with SQLite or Python layers.

## ADDED Requirements

### Requirement: Display Final Score alongside Price
The dashboard SHALL display the composite Final Score ($\in [-1.0, +1.0]$) overlaid with the BTC asset price at the daily level. This visualization MUST utilize TradingView Lightweight Charts as defined in the Presentation Layer architecture. Mathematical bounds for the score align with the Ensemble Aggregation outputs discussed in pi_final_research_lttd_01.md.

#### Scenario: Successful load of daily Final Score
- **WHEN** the dashboard-lttd-chart connects to the backend API and receives the daily LTTD dataset
- **THEN** the chart MUST render the BTC price using candlestick series
- **THEN** the chart MUST render the Final Score on an independent, bounded axis between -1.0 and +1.0
- **THEN** the rendered Final Score value at the last confirmed bar MUST match the Layer 5 Execution Engine state exactly
