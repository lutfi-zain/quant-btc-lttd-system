# pipeline-orchestrator Specification

## Purpose
TBD - created by archiving change p07-e2e-pipeline-runner. Update Purpose after archive.

## Requirements

### Requirement: End-to-End Execution Sequence
The system SHALL sequentially execute Layer 1 (Regime Detection) through Layer 5 (Execution Engine) at the **daily level**, ensuring outputs from Layer N-1 are cleanly passed to Layer N without circular dependencies.

#### Scenario: Successful full pipeline execution
- **GIVEN** a valid set of OHLCV daily data and synchronized On-Chain Metrics
- **WHEN** the pipeline orchestrator is invoked for a daily execution run
- **THEN** the pipeline SHALL produce a Final Score ∈ [-1.0, +1.0], generate a regime-weighted position sizing output, and successfully write exactly one `daily_lttd` row to the SQLite WAL database.

### Requirement: Strict Causal Continuity
The orchestrator SHALL strictly enforce that all indicator scores and feature processing are causal, preventing Lookahead Bias at the **bar level**.

#### Scenario: Verification of causality
- **GIVEN** a dataset of historical price and metric bars up to day `t`
- **WHEN** processing features via the Signal Engine at day `t`
- **THEN** the orchestrator SHALL mathematically assert that no Causal Filter accesses data at `t+k` (where `k > 0`), enforcing the rules outlined in `pi_final_research_lttd_01.md`.

### Requirement: VIF Pruning Invocation
The orchestrator SHALL invoke PCA Orthogonalization and Variance Inflation Factor (VIF) pruning dynamically during Layer 3 execution at the **regime level** before passing signals to the Ensemble Model.

#### Scenario: Multicollinear indicator rejection
- **GIVEN** the Signal Engine outputs 12 Technical Indicators where 9 have a VIF > 10
- **WHEN** the Feature Processing layer is orchestrated prior to aggregation
- **THEN** the system SHALL orthogonalize or drop collinear indicators such that the final matrix passed to the Ensemble Model contains exactly 0 features with VIF > 10, preventing synchronized failure risk.

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
