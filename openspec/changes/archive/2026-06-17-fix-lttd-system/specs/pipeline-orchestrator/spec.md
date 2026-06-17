## MODIFIED Requirements

### Requirement: Pipeline maps HMM regime to 5-level regime

The pipeline SHALL map the HMM regime (`BULL`/`BEAR`/`SIDEWAYS`) to the 5-level regime (`Strong Bull`/`Weak Bull`/`Neutral`/`Weak Bear`/`Strong Bear`) before passing to the execution engine. The mapping SHALL be based on the final_score value.

#### Scenario: Regime name mapping

- **WHEN** the pipeline computes `final_regime_hmm = "BULL"`
- **AND** `final_score = 0.8`
- **THEN** the regime passed to execution engine SHALL be `"Strong Bull"` (score >= 0.6)

#### Scenario: Regime mapping table

- **WHEN** `final_score >= 0.6`
- **THEN** regime SHALL be `"Strong Bull"`
- **WHEN** `final_score >= 0.2` and `< 0.6`
- **THEN** regime SHALL be `"Weak Bull"`
- **WHEN** `final_score >= -0.2` and `< 0.2`
- **THEN** regime SHALL be `"Neutral"`
- **WHEN** `final_score >= -0.6` and `< -0.2`
- **THEN** regime SHALL be `"Weak Bear"`
- **WHEN** `final_score < -0.6`
- **THEN** regime SHALL be `"Strong Bear"`

#### Scenario: Production exposure > 0

- **WHEN** the pipeline runs in production
- **AND** `final_score = 0.5`
- **THEN** `target_exposure` SHALL be > 0 (not 0.0)
- **AND** the regime SHALL be `"Weak Bull"` (not `"BULL"`)

### Requirement: Pipeline inverts signal before execution

The pipeline SHALL multiply `final_score` by -1 to convert contrarian IC to momentum IC. This inversion SHALL happen after ensemble computation and before regime mapping.

#### Scenario: Signal inversion

- **WHEN** the ensemble computes `final_score = -0.3`
- **THEN** after inversion, the score SHALL be `0.3`
- **AND** the regime SHALL be `"Weak Bull"` (not `"Weak Bear"`)

#### Scenario: Inversion preserves magnitude

- **WHEN** the ensemble computes `final_score = 0.8`
- **THEN** after inversion, the score SHALL be `-0.8`
- **AND** the regime SHALL be `"Strong Bear"` (not `"Strong Bull"`)

### Requirement: Pipeline aligns with backtest purge days

The pipeline SHALL use `purge_days=14` (matching the backtest runner) instead of `purge_days=7`.

#### Scenario: Purge days consistency

- **WHEN** the pipeline computes `train_idx_purged`
- **THEN** the purge window SHALL be 14 days (not 7 days)
- **AND** the purge SHALL match the backtest runner's behavior

#### Scenario: Backtest-production alignment

- **WHEN** the backtest runner processes date `t`
- **AND** the pipeline processes date `t`
- **THEN** the training window SHALL be identical (same purge days)

### Requirement: Pipeline uses score-based regime for sizing

The pipeline SHALL use the score-based 5-level regime (not HMM regime) for the `calculate_target_exposure()` function call.

#### Scenario: Sizing uses score-based regime

- **WHEN** the pipeline calls `calculate_target_exposure(final_score, regime)`
- **THEN** `regime` SHALL be the 5-level regime from score mapping
- **AND** `regime` SHALL NOT be the HMM regime (`BULL`/`BEAR`/`SIDEWAYS`)
