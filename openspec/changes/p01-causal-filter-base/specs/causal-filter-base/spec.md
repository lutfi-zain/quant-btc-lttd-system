## ADDED Requirements

### Requirement: Causal Filter Base Class
The system SHALL provide a `CausalFilter` abstract base class within the Signal Engine layer. All OHLCV-derived Technical Indicators MUST inherit from this base class to ensure strict structural compliance with real-time causal constraints at the bar level.

#### Scenario: Implementing a new Technical Indicator
- **GIVEN** a developer is building a new OHLCV-derived Technical Indicator
- **WHEN** the indicator is added to the Signal Engine layer
- **THEN** it MUST inherit from the `CausalFilter` abstract base class and implement its required abstract methods to output an Indicator Score ∈ {-1, +1} at the bar level.

### Requirement: Lookahead Bias Prevention Guardrails
The system SHALL algorithmically enforce that no Technical Indicator accesses future data points at the bar level (e.g., using symmetric windows or referencing `source[t+k]` where `k > 0`). The use of signal processing libraries (such as `scipy.signal`) MUST be restricted strictly to causal topologies, cross-referencing the mathematical proofs in `pi_final_research_lttd_01.md` regarding the elimination of lookahead bias.

#### Scenario: Applying a signal processing filter
- **GIVEN** a Technical Indicator computing an Indicator Score at the current bar `t`
- **WHEN** the indicator processes the OHLCV data array
- **THEN** the calculation MUST only reference historical or current observations (indices `<= t`) and the system MUST prevent the use of centered filters like `savgol_filter`.

### Requirement: Lookahead Verification Utility
The system SHALL provide a `test_no_lookahead()` computational verification utility. This utility MUST prove that appending future OHLCV bars (`t+1...t+N`) to a time-series does not alter the historical Indicator Score computed at bar `t`.

#### Scenario: Running the Lookahead Bias test suite
- **GIVEN** an array of OHLCV data truncated at bar `t` and the same array extended with future bars up to `t+N`
- **WHEN** the `test_no_lookahead()` utility evaluates the Technical Indicator on both datasets
- **THEN** the Indicator Score output at bar `t` MUST be exactly identical in both cases, proving strict causality at the bar level.

## Non-Goals
- Implementing concrete Technical Indicators (e.g., Kalman RSI, FDI). This specification only defines the abstract base class and causality constraints.
- Building the OHLCV data ingestion pipelines.
- Performing PCA Orthogonalization or VIF calculations (which are scoped to the Feature Processing layer).
