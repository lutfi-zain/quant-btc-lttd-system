# regime-weighted-sizing Specification

## Purpose
TBD - created by archiving change p06-execution-engine. Update Purpose after archive.
## Requirements
### Requirement: Binary 2-State Position Sizing
The execution engine MUST calculate target BTC exposure based on a strict 2-state boundary derived purely from the numeric `final_score`. It MUST NOT use the 5-state categorical regime string for capital allocation decisions. 
*   If `final_score >= 0.5`, the target exposure MUST be 1.0 (100% long).
*   If `final_score < 0.5`, the target exposure MUST be 0.0 (100% cash).
*   The `regime` string argument MAY still be accepted by the function signature for backward compatibility but MUST NOT dictate the output.

#### Scenario: Final score is exactly at the bull threshold
- **GIVEN** the daily ensemble calculation completes
- **WHEN** the `final_score` evaluated is exactly `0.5`
- **THEN** the function `calculate_target_exposure` MUST return a float `1.0` (100% BTC)

#### Scenario: Final score is just below the bull threshold
- **GIVEN** the daily ensemble calculation completes
- **WHEN** the `final_score` evaluated is `0.499`
- **THEN** the function `calculate_target_exposure` MUST return a float `0.0` (0% BTC / 100% Cash)

#### Scenario: Backward compatibility of function signature
- **GIVEN** the legacy `BacktestRunner` pipeline passes both `final_score` and `regime`
- **WHEN** `calculate_target_exposure` is called with `final_score=0.9` and `regime="Strong Bull"`
- **THEN** the function MUST return `1.0` without raising a TypeError or ValueError for the unused string parameter.

### Requirement: No lookahead bias in sizing
The position sizing logic SHALL NOT use any future data points. All decisions MUST be made using the `Final Score` and `Regime` computed from causal filters and historical observations.

#### Scenario: Verifying causal execution
- **GIVEN** a historical backtest or live execution sequence
- **WHEN** computing the target exposure for bar `t`
- **THEN** the output SHALL exactly match regardless of whether bars `t+1` to `t+N` are provided to the engine

