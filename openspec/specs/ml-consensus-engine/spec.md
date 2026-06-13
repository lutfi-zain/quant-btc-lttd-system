# ml-consensus-engine Specification

## Purpose
TBD - created by archiving change trend-following-ml-consensus. Update Purpose after archive.
## Requirements
### Requirement: ML-Based Ensemble Aggregation
The system MUST aggregate the normalized [0,1] technical and on-chain indicators using a machine learning model with L1-regularization (e.g., Lasso) and monotonic constraints.

#### Scenario: Dropping Redundant Indicators
- **GIVEN** an indicator matrix containing highly collinear indicators (VIF > 10)
- **WHEN** the ML consensus engine is trained via Walk-Forward Optimization
- **THEN** the L1-regularization MUST set the weights of the redundant indicators to exactly 0.0, retaining only the mathematically orthogonal signals.

#### Scenario: Regime Classification Boundaries
- **GIVEN** the ML consensus engine outputs a continuous Final Score ∈ [0.0, 1.0]
- **WHEN** mapping the score to the categorical Regime state
- **THEN** the system MUST map scores >0.8 to Strong Bull, >0.6 to Weak Bull, >0.4 to Neutral, >0.2 to Weak Bear, and <=0.2 to Strong Bear.

#### Scenario: Model Target Matching
- **GIVEN** the historical ground truth target `isp-regimes-btcusd.csv`
- **WHEN** training the ML consensus engine
- **THEN** the target MUST be forward-filled to provide a daily continuous target variable, and the model's WFO validation error MUST be measured against this target.

