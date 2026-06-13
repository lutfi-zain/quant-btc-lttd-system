## ADDED Requirements

### Requirement: Causal Rolling Normalization
All Technical Indicators and On-Chain Metrics MUST be normalized to a strict continuous [0.0, 1.0] bound using a causal, lookahead-free rolling window before being passed to the ensemble aggregator.

#### Scenario: Computing Indicator Score
- **GIVEN** an unbounded metric (e.g., `sth_nupl`) at time `t`
- **WHEN** the rolling normalization is applied
- **THEN** the system MUST use ONLY data from `t-N` to `t` (where N is the lookback period, e.g., 800 days) to compute the bounds, ensuring the output is exactly bounded ∈ [0.0, 1.0] and mathematically causal.

#### Scenario: Preventing Lookahead Bias
- **GIVEN** a historical backtest execution over the year 2017
- **WHEN** normalizing a value on 2017-06-14
- **THEN** the rolling minimum and maximum MUST NOT incorporate any data from 2017-06-15 or later, adhering strictly to the `pi_final_research_lttd_01.md` causal constraint.
