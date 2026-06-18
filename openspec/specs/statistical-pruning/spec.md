# Capability: Statistical Pruning

## Purpose
TBD

## Requirements

### Requirement: Prevent Dummy Variable Trap (Bar Level)
The feature matrix generation layer MUST drop exactly one HMM posterior probability column before feeding data to the Ensemble layer to prevent probability leakage and infinite VIF.

#### Scenario: Dropping redundant HMM posterior
- **GIVEN** the HMM produces daily level posteriors `p_bull`, `p_bear`, and `p_sideways`
- **WHEN** the feature matrix is constructed for the Ensemble Aggregation layer
- **THEN** the `p_sideways` column MUST be dropped, leaving only `p_bull` and `p_bear`.

### Requirement: Dynamic VIF Pruning for On-Chain Metrics (Regime Level)
If multiple On-Chain Metrics display multicollinearity (VIF > 10), the VIF filter MUST iteratively drop the most collinear or least predictive feature (e.g., using Pratt's Measure) until all remaining features have VIF <= 10.

#### Scenario: Dropping collinear MVRV or NUPL
- **GIVEN** `sth_mvrv` and `sth_nupl` are both included in the feature matrix
- **WHEN** their computed VIF exceeds 10
- **THEN** the feature processing pipeline MUST drop the redundant metric and the final Feature Processing output MUST contain features with max VIF < 10.
