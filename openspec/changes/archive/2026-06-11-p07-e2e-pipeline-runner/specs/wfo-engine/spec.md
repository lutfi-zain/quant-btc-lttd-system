# Capability: wfo-engine

## Non-Goals
- Real-time trading execution or broker integration.
- Backtesting frequency higher than daily level.
- Live paper trading state management.

## ADDED Requirements

### Requirement: Rolling Window WFO Splitting
The engine SHALL slice the historical data into rolling Walk-Forward Optimization (WFO) windows, specifically 3 years for training, 6 months for validation, and 6 months for testing, rolling forward iteratively at the **regime level**.

#### Scenario: WFO window generation
- **GIVEN** 8 years of historical BTC daily data
- **WHEN** the wfo-engine initializes the backtest sequence
- **THEN** it SHALL output strict date boundaries for each iteration where `train_len = 1095 days`, `val_len = 180 days`, and `test_len = 180 days`, returning exactly `N` number of contiguous test periods.

### Requirement: Combinatorial Purged Cross-Validation (CPCV)
The engine SHALL purge adjacent training bars that overlap with the validation or test windows to eliminate leakage and Lookahead Bias at the **daily level** during the Ensemble Model fitting.

#### Scenario: Purging embargo boundaries
- **GIVEN** an iteration's train/validate/test split defined by the WFO engine
- **WHEN** the Ensemble Model (L1-Lasso Logistic Regression) requests the training set
- **THEN** the engine SHALL purge an embargo period corresponding to the maximum indicator lookback (e.g., up to 350 days based on OU Half-Life) between the train and test splits, guaranteeing 0 overlapping samples as per `pi_final_research_lttd_01.md`.

### Requirement: Stable Out-of-Sample Evaluation
The engine SHALL aggregate the test sets across all rolling windows to compute the true out-of-sample performance metrics at the **regime level**.

#### Scenario: Out-of-sample scoring
- **GIVEN** the Execution Engine has produced a series of daily LTTD Final Scores over multiple WFO iterations
- **WHEN** the backtest run completes
- **THEN** the engine SHALL report the aggregated out-of-sample Sharpe ratio (target 1.8 - 2.2) and confirm maximum drawdown is mathematically constrained strictly below 25.0%.
