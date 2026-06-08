## ADDED Requirements

### Requirement: Adaptive Fourier Supertrend Causal Implementation
The Adaptive Fourier Transform Supertrend MUST be implemented as a `Technical Indicator` in Layer 2 (Signal Engine), inheriting from the `CausalFilter` base class. This applies at the **daily level**.

#### Scenario: Causal Signal Generation
- **GIVEN** a continuous series of daily OHLCV data
- **WHEN** the indicator calculates the trend over a rolling window
- **THEN** it MUST output a binary `Indicator Score` exactly ∈ {-1, +1} for every completed daily bar, utilizing only causal offsets `source[i]` where i ≥ 0 (no future bars).

### Requirement: Lookahead Bias Elimination Verification
The indicator MUST structurally prevent any future data from influencing past calculations, complying with the anti-leakage mandate defined in the research findings. This applies at the **bar level**.

#### Scenario: Future Data Invariance Test
- **GIVEN** an array of `Indicator Score` values calculated up to day `t`
- **WHEN** new daily OHLCV bars `t+1...t+N` are appended to the dataset and the filter recalculates
- **THEN** the previously calculated `Indicator Score` at day `t` MUST remain mathematically identical to its original value, passing the `test_no_lookahead()` unit test.

### Requirement: Spectral Frequency Dominance (Orthogonality)
The indicator MUST isolate dominant market cycles dynamically in the frequency domain, fulfilling the role of "Indicator 5 (Spectral Trend)" as recommended in the `Alternative: Causal Pine Script Engine` section of `pi_final_research_lttd_01.md`. This applies at the **regime level**.

#### Scenario: Variance Inflation Factor Validation
- **GIVEN** a matrix of technical indicator signals passed to Layer 3 (Feature Processing)
- **WHEN** the system calculates the Variance Inflation Factor (VIF) during PCA Orthogonalization
- **THEN** the VIF for the Adaptive Fourier Supertrend MUST be < 10, confirming it provides statistically orthogonal information compared to smoothed momentum (e.g., Kalman RSI).

### Requirement: Integration with the Ensemble Aggregation Layer
The binary `Indicator Score` produced by the Adaptive Fourier Supertrend MUST be correctly integrated into the WFO-trained ensemble. This applies at the **daily level**.

#### Scenario: WFO Pipeline Ingestion
- **GIVEN** the `Indicator Score` ∈ {-1, +1} produced by the Adaptive Fourier Supertrend
- **WHEN** passed to Layer 4 (Ensemble Aggregation) for Walk-Forward Optimization
- **THEN** it MUST successfully map as a standalone predictor for the L1-Lasso Logistic Regression model without inducing any type errors, contributing to the `Final Score` ∈ [-1.0, +1.0].

## Non-Goals
- DO NOT implement a centered or symmetric Savitzky-Golay Filter (Indicator 12); this specification is strictly for the Adaptive Fourier Supertrend.
- DO NOT introduce any external API calls; the Fourier transform must operate strictly on standard OHLCV price action data.
- DO NOT generate continuously variable scores (e.g., floats between -1.0 and +1.0); the raw output of this Layer 2 indicator must be strictly binary ∈ {-1, +1} before ensemble aggregation.
