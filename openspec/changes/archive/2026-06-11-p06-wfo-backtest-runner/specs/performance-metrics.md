## Non-Goals
- Providing intraday or minute-level performance metrics.
- Graphical visualization plotting (this is handled by Layer 6: Presentation).

## ADDED Requirements

### Requirement: Out-of-Sample Metric Aggregation
At the regime level and aggregate level, the backtest runner must compute and report statistically sound metrics strictly from the out-of-sample test windows.

#### Scenario: Computing the Sharpe ratio and maximum drawdown
- **GIVEN** the WFO backtest runner has completed all rolling iterations
- **WHEN** the aggregated out-of-sample daily returns are collected from the historical simulation adapter
- **THEN** the system SHALL calculate the annualized Sharpe ratio and maximum drawdown over the entire backtest, ensuring no lookahead bias influenced the trade entries.

#### Scenario: Hit rate measurement by Regime
- **GIVEN** the system records trades taken during different Regimes (Bull, Bear, Sideways)
- **WHEN** evaluating the out-of-sample trade profitability
- **THEN** the runner SHALL report the win rate (hit rate) specifically partitioned by the HMM-inferred Regime state.
