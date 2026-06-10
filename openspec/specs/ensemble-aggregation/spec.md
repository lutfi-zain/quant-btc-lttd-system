# ensemble-aggregation Specification

## Purpose
TBD - created by archiving change p05-ensemble-aggregation. Update Purpose after archive.
## Requirements
### Requirement: L1-Lasso Logistic Regression Ensemble
At the daily level, the Ensemble Aggregation layer MUST fit an L1-Lasso Logistic Regression model on the PCA-orthogonalized features to predict the Final Score. The Final Score MUST be probabilistically bounded within the range `[-1.0, +1.0]`.

#### Scenario: Final Score Generation
- **GIVEN** the daily PCA-orthogonalized features
- **WHEN** the L1-Lasso Logistic Regression model processes the features
- **THEN** the output Final Score MUST be a float bounded in `[-1.0, +1.0]`

### Requirement: Pratt's Measure Calculation
At the regime level, the Ensemble Aggregation layer MUST compute Pratt's Measure (`dⱼ = βⱼ · rⱼ / R²`) to quantify the relative importance of each indicator after controlling for collinearity, as mathematically specified in `pi_final_research_lttd_01.md`.

#### Scenario: Pratt's Measure Evaluation
- **GIVEN** a fitted L1-Lasso Logistic Regression model and orthogonalized features
- **WHEN** the feature importance is evaluated
- **THEN** the sum of Pratt's Measures for all features MUST equal 1.0 (or 100%)
- **THEN** the absolute Pratt's Measure for each feature MUST be explicitly measurable

