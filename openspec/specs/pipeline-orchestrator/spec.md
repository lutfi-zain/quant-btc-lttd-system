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

