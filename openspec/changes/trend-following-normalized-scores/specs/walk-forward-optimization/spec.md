## MODIFIED Requirements

### Requirement: WFO Target Variable (Regime Transition)
At the regime level, the WFO pipeline MUST train models to predict regime transitions rather than next-day return signs. The target variable SHALL be the regime label at time t+1 (one of: "Strong Bull", "Weak Bull", "Neutral", "Weak Bear", "Strong Bear").

#### Scenario: Regime Transition Target
- **GIVEN** historical daily data with regime labels
- **WHEN** the WFO pipeline constructs training targets
- **THEN** the target variable at time t SHALL be the regime label at time t+1
- **AND** the target variable SHALL NOT use next-day return sign (np.sign(close[t+1] - close[t]))

#### Scenario: WFO Fold with Regime Targets
- **GIVEN** a walk-forward optimization split with training fold ending at t_train
- **WHEN** constructing the target vector
- **THEN** the last training observation at t_train SHALL be purged to prevent leakage
- **AND** the target values SHALL be regime labels, not return signs

### Requirement: WFO Component Threshold Optimization
At the regime level, the WFO pipeline MUST optimize component `buy_threshold` and `sell_threshold` parameters for each regime. The optimization objective SHALL maximize ISP signal alignment.

#### Scenario: Threshold Optimization per Regime
- **GIVEN** a training window with historical regime labels and ISP signals
- **WHEN** the WFO pipeline optimizes component thresholds
- **THEN** the optimal thresholds SHALL be stored per regime (Strong Bull, Weak Bull, Neutral, Weak Bear, Strong Bear)
- **AND** the optimization SHALL use ISP signal alignment as the objective function

## MODIFIED Requirements (additional)

### Requirement: WFO Pipeline Execution (updated)
At the regime level, the system MUST perform Walk-Forward Optimization (WFO). The rolling pipeline MUST train on a 3-year window, validate on a 6-month window, and test on a 6-month out-of-sample window. The pipeline MUST now optimize component thresholds in addition to model parameters.

#### Scenario: Rolling Window with Threshold Optimization
- **GIVEN** historical daily data spanning multiple years
- **WHEN** the WFO pipeline advances to the next step
- **THEN** the training window MUST optimize both HMM parameters and component thresholds
- **AND** the out-of-sample test MUST evaluate ISP signal alignment, not just R²
