# onchain-regime-filter Specification

## Purpose
TBD - created by archiving change p03-onchain-signals. Update Purpose after archive.
## Requirements
### Requirement: STH-NUPL Euphoric Regime Filter
The system SHALL apply an overriding filter to the HMM posterior probabilities when Short-Term Holder Net Unrealized Profit/Loss (STH-NUPL) exceeds euphoric thresholds. This requirement applies at the **regime level**. Cross-reference: pi_final_research_lttd_01.md Section "On-Chain Lead-Lag Asymmetry".

#### Scenario: STH-NUPL extreme threshold
- **GIVEN** the Layer 1 Regime Detection outputs a `BULL` state probability > 0.80
- **WHEN** the normalized On-Chain Metric `sth_nupl` value is > 0.75
- **THEN** the system scales down the maximum exposure by deterministically reducing the `BULL` regime probability weight to <= 0.50, overriding the HMM posterior probability to trigger risk-off execution.

### Requirement: STH-MVRV Capitulation and Euphoria Heuristics
The system SHALL utilize the STH-MVRV ratio to detect market capitulation and cycle tops, modifying the baseline HMM Regime state. This applies at the **regime level**.

#### Scenario: STH-MVRV cycle top detection
- **GIVEN** the current LTTD epoch window is active and the system is long
- **WHEN** the `sth_mvrv` value crosses above 2.0
- **THEN** the system limits `BULL` Regime confidence, feeding a risk-off signal modifier to Layer 5 Execution Engine resulting in a Final Score <= 0.0.

### Requirement: On-Chain Metric Feature Orthogonalization
The rate of change (momentum) of On-Chain Metrics (e.g., 7-day momentum of `sth_sopr_24h`) SHALL be fed into Layer 3 (Feature Processing) as candidate features, provided they pass multicollinearity checks. This applies at the **bar level**.

#### Scenario: VIF pruning of correlated on-chain metrics
- **GIVEN** the Layer 3 Feature Processing matrix includes 7-day momentum of `sth_sopr_24h` and multiple OHLCV Technical Indicators
- **WHEN** the Variance Inflation Factor (VIF) is calculated across the entire feature set before PCA Orthogonalization
- **THEN** the system drops any indicator with VIF > 10, ensuring only mathematically orthogonal features reach the Layer 4 Ensemble Aggregation.

