# feature-diagnostics-panel Specification

## Purpose
TBD - created by archiving change p09-frontend-panels.

## Requirements

### Requirement: Feature Matrix and Collinearity Diagnostics
The feature-diagnostics-panel SHALL visualize the individual causal Indicator Scores ($\in \{-1, +1\}$), PCA variance explained, and Variance Inflation Factor (VIF) metrics at the daily level. This ensures visual enforcement of the multicollinearity bounds where no single Technical Indicator exhibits $VIF > 10$, adhering to the Feature Processing layer rules in pi_final_research_lttd_01.md.

#### Scenario: Identifying highly collinear indicators
- **WHEN** the feature-diagnostics-panel renders the Layer 3 output metrics
- **THEN** the panel MUST display the daily Indicator Score ($\in \{-1, +1\}$) for each Technical Indicator
- **THEN** the panel MUST visually flag any indicator that records a VIF value $> 10$ as a critical warning
- **THEN** the panel MUST show the cumulative variance explained by the top PCA Orthogonalization components as a percentage $> 85\%$
