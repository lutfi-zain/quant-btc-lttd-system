## ADDED Requirements

### Requirement: Causal Fractal Dimension Index (FDI) Oscillator
This requirement applies at the bar level. The system MUST compute the Fractal Dimension Index to quantify topological randomness and market efficiency without referencing future data points.

#### Scenario: FDI calculation enforces zero lookahead bias
- **WHEN** the `fdi-oscillator` calculates the index for the current bar `t`
- **THEN** it MUST subclass the `CausalFilter` base class
- **AND THEN** it MUST only reference data from bars `t` and earlier (no centered/symmetric windows)

#### Scenario: FDI generates directional signal
- **WHEN** the `fdi-oscillator` is evaluated
- **THEN** it MUST classify a dimension `D < 1.5` as a trending state and `D >= 1.5` as a mean-reverting state
- **AND THEN** it MUST output an Indicator Score ∈ {-1, +1} representing the local momentum direction


### Requirement: Robust Quantile DEMA Extraction
This requirement applies at the bar level. The system MUST calculate a Quantile Double Exponential Moving Average to handle heavy-tailed return distributions robustly.

#### Scenario: Quantile DEMA enforces zero lookahead bias
- **WHEN** the `quantile-dema` calculates the trend line for the current bar `t`
- **THEN** it MUST subclass the `CausalFilter` base class
- **AND THEN** it MUST NOT use symmetric smoothing windows

#### Scenario: Quantile DEMA generates directional signal
- **WHEN** the current price interacts with the computed quantile-based bands
- **THEN** it MUST output an Indicator Score ∈ {-1, +1} representing the robust trend direction


### Requirement: Causal Advanced Stochastic Oscillator
This requirement applies at the bar level. The system MUST calculate an advanced bounded stochastic oscillator to pinpoint local macro-reversals in extreme ranges.

#### Scenario: Advanced Stochastic enforces zero lookahead bias
- **WHEN** the `advanced-stochastic` evaluates the dynamic high-low window for the current bar `t`
- **THEN** it MUST subclass the `CausalFilter` base class
- **AND THEN** it MUST only evaluate bounds up to bar `t` without future data leakage

#### Scenario: Advanced Stochastic generates directional signal
- **WHEN** the oscillator crosses predefined exhaustion thresholds
- **THEN** it MUST output an Indicator Score ∈ {-1, +1} signaling the reversal


### Requirement: Non-Goals for Batch 3 Technical Indicators
This requirement outlines the boundaries for the Layer 2 (Signal Engine) implementations.

#### Scenario: Avoid multicollinearity resolution in signal layer
- **WHEN** any Batch 3 indicator is executed
- **THEN** it MUST NOT perform multicollinearity checks (VIF) or PCA orthogonalization
- **AND THEN** it MUST rely on Layer 3 (Feature Processing) to handle these transformations

#### Scenario: Avoid ensemble aggregation in signal layer
- **WHEN** any Batch 3 indicator produces an Indicator Score
- **THEN** it MUST NOT attempt to combine scores into a Final Score
- **AND THEN** it MUST defer final classification to Layer 4 (Ensemble Aggregation)
