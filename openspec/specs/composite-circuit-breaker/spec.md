# composite-circuit-breaker Specification

## Purpose
TBD - created by archiving change composite-oscillator-circuit-breaker. Update Purpose after archive.

## Requirements

### Requirement: Execution Circuit Breaker
Layer 5 (Execution Engine) MUST intercept the sizing calculation and enforce a hard stop (0% exposure) if the market is structurally overvalued, overriding the HMM Regime and Ensemble Momentum scores.

#### Scenario: Euphoric Top Detection
- **WHEN** the daily `composite_value` is `<= -3.454738910743079`
- **THEN** the Execution Engine MUST set `target_exposure = 0.0`.
- **AND** this rule MUST override any BULL regime or positive ensemble momentum signal.

#### Scenario: Circuit Breaker Cool-off
- **WHEN** the circuit breaker has been engaged (exposure forced to 0.0)
- **THEN** it MUST remain engaged (exposure = 0.0) until the `composite_value` rises above `0.8491614227097739` (meaning structural valuation has cooled down).
- **AND** only when `composite_value > 0.8491614227097739` will normal HMM-based sizing resume.

#### Scenario: Normal Market Operations
- **WHEN** the `composite_value` is `> 0.8491614227097739` and the circuit breaker is NOT currently engaged
- **THEN** the execution engine MUST calculate the binary exposure strictly based on the standard HMM Regime logic (1.0 for BULL, 0.0 for BEAR, etc.).

#### Scenario: Deep Value Accumulation Override
- **WHEN** the `composite_value` is `>= 2.000613` and the calculated exposure is `0.0`
- **THEN** the Execution Engine MUST force target exposure to `1.0`.

## Non-Goals
- This logic applies ONLY at the Execution Layer (Layer 5). The HMM probabilities and Ensemble scores MUST still be calculated normally in the database for tracking purposes. The circuit breaker does NOT alter the underlying signal computation, only the applied exposure sizing.
