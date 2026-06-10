# pca-orthogonalization Specification

## Purpose
TBD - created by archiving change p04-feature-processing. Update Purpose after archive.
## Requirements
### Requirement: PCA Orthogonalization of Indicator Matrix
The system SHALL apply Principal Component Analysis (PCA) to the daily level matrix of Technical Indicators and On-Chain Metrics. This transformation MUST mathematically convert the noisy, collinear raw signals into an orthogonal feature space. Mathematical rationale is detailed in `pi_final_research_lttd_01.md` Section "Orthogonalization".

#### Scenario: Transforming collinear signals
- **GIVEN** a raw indicator matrix produced by the Signal Engine at the daily level
- **WHEN** the PCA transformation is applied
- **THEN** the system SHALL output a set of orthogonal principal components where the cross-correlation between any two components is exactly 0.0

### Requirement: Variance Retention Threshold
The PCA Orthogonalization process SHALL retain the minimum number of principal components necessary to capture >85% of the system's variance. The remaining components MUST be discarded to reduce noise before passing to the Ensemble Aggregation layer.

#### Scenario: Component selection for variance capture
- **GIVEN** the full set of principal components generated from the indicator matrix
- **WHEN** selecting components for the Ensemble Aggregation layer
- **THEN** the system SHALL retain only the top components that cumulatively explain >85.0% of the total variance

### Requirement: Strict Causal Transformation
The PCA transformation MUST operate strictly within causal boundaries at the daily level. The PCA projection matrix MUST be fit exclusively on historical training data within the Walk-Forward Optimization (WFO) window and then applied to out-of-sample data, eliminating any Lookahead Bias.

#### Scenario: Out-of-sample feature projection
- **GIVEN** a Walk-Forward Optimization (WFO) rolling window setup
- **WHEN** projecting daily level features for the validation or test window
- **THEN** the system SHALL use the PCA transformation matrix fitted exclusively on the preceding training window, ensuring 0% leakage of future data

