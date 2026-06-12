# ou-halflife-estimator Specification

## Purpose
TBD - created by archiving change p02-ou-halflife-estimator. Update Purpose after archive.
## Requirements
### Requirement: OU Half-Life Statistical Estimation
The Feature Processing layer (Layer 3) SHALL estimate the Ornstein-Uhlenbeck (OU) mean-reversion half-life daily using a historical window of log price levels, directly referencing the mathematical specification in pi_final_research_lttd_01.md. This calculation applies at the daily level.

#### Scenario: Stable market mean-reversion
- **GIVEN** an active quantitative analysis session with sufficient confirmed daily OHLCV bars
- **WHEN** the daily OU Half-Life is computed on the log price levels
- **THEN** the estimated OU Half-Life MUST be calculated and returned
- **THEN** the resulting OU Half-Life MUST be strictly clamped to the established LTTD bounds of [120, 350] days

#### Scenario: Insufficient history for calibration
- **GIVEN** a newly initialized environment or truncated historical dataset
- **WHEN** the number of available historical daily bars is fewer than required for statistical significance
- **THEN** the OU Half-Life SHALL default to the conservative upper bound of 350 days

### Requirement: Log-Price OU Half-Life Calibration
Enforce that the Ornstein-Uhlenbeck (OU) mean-reversion speed estimation models price levels instead of returns.

#### Scenario: OU Half-Life Parameter Estimation
- **GIVEN** a historical price series.
- **WHEN** calibrating the AR(1) model for OU half-life.
- **THEN** the input series to the regression SHALL be log price levels ($\ln(\text{close})$) instead of log returns.

### Requirement: Periodic WFO Recalibration
During Walk-Forward Optimization (WFO), the system SHALL recalibrate the baseline OU Half-Life epoch parameters quarterly to prevent phase lag. This applies at the regime level.

#### Scenario: Quarterly WFO epoch transition
- **GIVEN** an executing Walk-Forward Optimization (WFO) backtest pipeline utilizing Combinatorial Purged Cross-Validation (CPCV)
- **WHEN** the WFO sliding window advances to a new quarter
- **THEN** the historical baseline for the OU Half-Life MUST be recalculated using the purged in-sample data
- **THEN** the recalibration MUST NOT use any out-of-sample data, strictly preventing Lookahead Bias

