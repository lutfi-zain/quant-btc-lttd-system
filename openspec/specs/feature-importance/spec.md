# feature-importance Specification

## Purpose
TBD - created by archiving change p04-feature-processing. Update Purpose after archive.
## Requirements
### Requirement: Pratt's Measure Calculation
The system SHALL calculate Pratt's Measure (`d_j = beta_j * r_j / R^2`) to quantify the relative importance of each Technical Indicator and On-Chain Metric at the daily level. This measure determines the feature's independent contribution to the Final Score after controlling for collinearity, as mathematically specified in `pi_final_research_lttd_01.md` Section "Sources" (Reference 7 & 8).

#### Scenario: Evaluating indicator contribution
- **GIVEN** a fitted Ensemble Aggregation model predicting the Long-Term Trend Direction (LTTD) at the daily level
- **WHEN** the feature importance calculation is triggered
- **THEN** the system SHALL output Pratt's Measure for each input feature, with the sum of all measures equaling 100% (or 1.0) of the explained variance R^2

### Requirement: Importance Ranking and Reporting
The system SHALL rank the indicators based on their computed Pratt's Measure. This ranking MUST be used to audit the effectiveness of the Technical Indicators and On-Chain Metrics within a specific Regime (BULL, BEAR, or SIDEWAYS).

#### Scenario: Generating feature importance report
- **GIVEN** Pratt's Measure has been successfully calculated for all features
- **WHEN** generating the model audit report for a specific Regime
- **THEN** the system SHALL rank the features by Pratt's Measure and flag any feature where d_j < 0.01 (less than 1% contribution) for potential removal

