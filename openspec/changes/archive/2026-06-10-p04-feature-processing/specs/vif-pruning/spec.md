## ADDED Requirements

### Requirement: Variance Inflation Factor (VIF) Computation
The system SHALL compute the Variance Inflation Factor (VIF) for the matrix of Technical Indicator and On-Chain Metric values at the daily level. This calculation identifies multicollinearity among the input features. Mathematical reference is located in `pi_final_research_lttd_01.md` Section "Multicollinearity in 12 Technical Indicators".

#### Scenario: Redundant indicator detection
- **GIVEN** a matrix of Technical Indicator and On-Chain Metric values at the daily level
- **WHEN** two or more indicators have a calculated VIF > 10
- **THEN** the system SHALL flag these specific indicators as highly collinear with a measurable VIF score > 10.0

### Requirement: Iterative VIF Pruning
The system SHALL support an iterative pruning process at the daily level. It MUST recursively calculate VIF and drop the feature with the highest VIF until all remaining features have a VIF <= 10, protecting the Ensemble Model from over-confident synchronized failures.

#### Scenario: Automated feature pruning
- **GIVEN** an indicator matrix containing features with VIF > 10
- **WHEN** the VIF pruning process is invoked
- **THEN** the system SHALL iteratively remove the indicator with the highest VIF until the maximum VIF of all remaining indicators is <= 10.0

## Non-Goals
- Real-time VIF computation at the tick or sub-daily bar level (this is strictly a daily level operation).
- Subjective selection of which collinear feature to keep (the algorithm strictly drops the highest VIF feature iteratively).
