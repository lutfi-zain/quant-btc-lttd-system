# Capability: Regime Classification

## Purpose
TBD

## Requirements

### Requirement: Strict Regime Vocabulary Enforcement (Daily Level)
The Regime Detection layer MUST output a single Regime label that strictly belongs to the ubiquitous language set: `BULL`, `BEAR`, or `SIDEWAYS`. Any granular sub-regimes inferred by the model must be mapped to one of these three states.

#### Scenario: Mapping granular states to standard Regimes
- **GIVEN** the HMM infers a state label such as "Strong Bull", "Weak Bear", or "Neutral"
- **WHEN** the Final Score and Regime are passed to the Execution Engine
- **THEN** the Regime output MUST be exactly one of: `BULL`, `BEAR`, `SIDEWAYS` (e.g., "Strong Bull" -> `BULL`, "Neutral" -> `SIDEWAYS`).
