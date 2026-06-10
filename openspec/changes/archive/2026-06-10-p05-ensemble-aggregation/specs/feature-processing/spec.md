# Feature Processing

## Non-Goals
- Generating causal Technical Indicator scores (Layer 2 responsibility).
- Optimizing or selecting the ensemble model (Layer 4 responsibility).
- Modifying or interpreting the HMM Regime (Layer 1 responsibility).

## ADDED Requirements

### Requirement: VIF Multicollinearity Pruning
At the daily level, the Feature Processing layer MUST compute the Variance Inflation Factor (VIF) for the indicator matrix. Indicators with VIF > 10 MUST be identified for pruning before aggregation, as mathematically specified in `pi_final_research_lttd_01.md`.

#### Scenario: VIF Threshold Exceeded
- **GIVEN** a matrix of causal Technical Indicator scores
- **WHEN** the computed VIF for any Technical Indicator is > 10
- **THEN** the system MUST mark the indicator for pruning (e.g., boolean flag `vif_prune = True`)
- **THEN** the number of pruned indicators MUST be explicitly logged and verifiable

### Requirement: PCA Orthogonalization
At the daily level, the Feature Processing layer MUST apply Principal Component Analysis (PCA) to the raw matrix of Indicator Scores. This orthogonalization MUST capture at least 85% of the variance from the first 3 components to prevent multicollinearity, referencing the findings in `pi_final_research_lttd_01.md`.

#### Scenario: Successful Orthogonalization
- **GIVEN** a raw matrix of Technical Indicator scores exhibiting multicollinearity
- **WHEN** PCA Orthogonalization is applied
- **THEN** the resulting principal components MUST be perfectly orthogonal (correlation coefficient ≈ 0)
- **THEN** the cumulative explained variance of the retained components MUST be >= 0.85
