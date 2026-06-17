## ADDED Requirements

### Requirement: ACF(1) target < 0.85

The system SHALL target ACF(1) < 0.85 for the final_score time series. This corresponds to a half-life of approximately 4 trading days.

#### Scenario: ACF(1) measurement

- **WHEN** the backtest runner computes the final_score time series
- **THEN** the ACF at lag 1 SHALL be computed
- **AND** the value SHALL be < 0.85

#### Scenario: ACF(1) monitoring

- **WHEN** the daily pipeline produces a final_score
- **THEN** the ACF(1) of the trailing 100 scores SHALL be logged
- **AND** an alert SHALL be raised if ACF(1) > 0.90

### Requirement: KalmanRSI lag reduction

The KalmanRSI indicator SHALL remove the Kalman filter pre-processing step. The RSI SHALL be computed directly on the close price without Kalman smoothing.

#### Scenario: KalmanRSI without Kalman filter

- **WHEN** KalmanRSI computes the indicator score
- **THEN** the RSI SHALL be computed on the raw close price
- **AND** the Kalman filter (Q=0.75, R=205) SHALL NOT be applied
- **AND** the RSI period SHALL be reduced from 250 to 50

#### Scenario: KalmanRSI output range

- **WHEN** KalmanRSI computes the indicator score
- **THEN** the output SHALL be a binary signal ∈ {-1, +1}
- **AND** the signal SHALL be computed from RSI position relative to 50-level

### Requirement: AdvancedStochastic period reduction

The AdvancedStochastic indicator SHALL compute stochastic oscillator for periods 1-30 only (reduced from 1-129). The output SHALL be the average of 30 binary trend signals.

#### Scenario: AdvancedStochastic with reduced periods

- **WHEN** AdvancedStochastic computes the indicator score
- **THEN** the stochastic oscillator SHALL be computed for periods 1 through 30
- **AND** the output SHALL be the mean of 30 binary signals
- **AND** periods 31-129 SHALL NOT be computed

#### Scenario: AdvancedStochastic computational cost

- **WHEN** AdvancedStochastic computes the indicator score
- **THEN** the computation time SHALL be reduced by approximately 75% (30 vs 129 periods)

### Requirement: RollingNormalizer window reduction

The RollingNormalizer SHALL use a maximum window of 200 days (reduced from 800 days). The minimum window SHALL remain at 200 days (unchanged).

#### Scenario: RollingNormalizer with reduced window

- **WHEN** RollingNormalizer normalizes indicator values
- **THEN** the rolling window SHALL be capped at 200 days
- **AND** the normalization SHALL use min/max over the trailing 200 days

#### Scenario: RollingNormalizer responsiveness

- **WHEN** a new extreme value enters the rolling window
- **THEN** the normalization SHALL adapt within 200 days (vs 800 days previously)

## MODIFIED Requirements

### Requirement: Indicator lag budget

Each indicator in the signal engine SHALL have a maximum lag budget of 100 days. Indicators exceeding this budget SHALL be flagged for review.

#### Scenario: Lag budget check

- **WHEN** the signal engine computes all indicator scores
- **THEN** the effective lag of each indicator SHALL be measured
- **AND** any indicator with lag > 100 days SHALL be flagged in diagnostics

#### Scenario: Lag budget compliance

- **WHEN** the signal engine runs in production
- **THEN** all indicators SHALL have lag < 100 days
- **AND** the average indicator lag SHALL be < 50 days
