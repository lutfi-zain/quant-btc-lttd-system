## ADDED Requirements

### Requirement: Regime-weighted position sizing
The Execution Engine SHALL compute a target BTC exposure (position size) ∈ [0.0, 1.0] dynamically by weighting the continuous `Final Score` ∈ [-1.0, +1.0] against the inferred `Regime` (BULL, BEAR, SIDEWAYS).

#### Scenario: High-conviction Bull regime scaling
- **GIVEN** a computed `Final Score` > 0.0 at the daily level
- **WHEN** the inferred `Regime` is BULL
- **THEN** the target exposure SHALL be directly proportional to the `Final Score` (e.g., exposure = `Final Score`), up to a maximum of 1.0

#### Scenario: Capital preservation in Bear regime
- **GIVEN** any computed `Final Score`
- **WHEN** the inferred `Regime` is BEAR
- **THEN** the target exposure SHALL be strictly 0.0 to protect against macro downtrends

#### Scenario: Risk dampening in Sideways regime
- **GIVEN** a computed `Final Score` > 0.0 at the daily level
- **WHEN** the inferred `Regime` is SIDEWAYS
- **THEN** the target exposure SHALL be scaled by the `Final Score` but hard-capped at 0.5 to minimize portfolio variance

### Requirement: No lookahead bias in sizing
The position sizing logic SHALL NOT use any future data points. All decisions MUST be made using the `Final Score` and `Regime` computed from causal filters and historical observations.

#### Scenario: Verifying causal execution
- **GIVEN** a historical backtest or live execution sequence
- **WHEN** computing the target exposure for bar `t`
- **THEN** the output SHALL exactly match regardless of whether bars `t+1` to `t+N` are provided to the engine

## Non-Goals
- Executing actual trades on an exchange (Layer 5 purely computes the mathematical target exposure; order execution is out of scope).
- Intraday position sizing (the engine operates strictly on the daily level).
