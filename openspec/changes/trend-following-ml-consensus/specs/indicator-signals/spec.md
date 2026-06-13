## MODIFIED Requirements

### Requirement: Continuous Indicator Output
The fundamental output contract of all Layer 2 Signal Engine indicators MUST be modified to return continuous intensities rather than discrete votes.

#### Scenario: Layer 2 Signal Output
- **GIVEN** any Technical Indicator or On-Chain Metric evaluated by the Signal Engine
- **WHEN** the `Indicator Score` is calculated for a given day
- **THEN** the value MUST be a continuous float ∈ [0.0, 1.0], replacing the legacy behavior which emitted discrete {-1, +1} integers.
