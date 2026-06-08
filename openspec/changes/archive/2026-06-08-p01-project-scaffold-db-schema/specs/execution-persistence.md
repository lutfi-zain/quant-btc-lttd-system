## ADDED Requirements

### Requirement: Idempotent Execution Logging
Layer 5 (Execution Engine) MUST provide write abstractions that ensure daily execution outputs (`Final Score`, `Regime`, `Indicator Score`s) are written idempotently to the database to prevent duplicate entries for the same daily bar. This requirement applies at the daily level.

#### Scenario: Idempotent Write of Daily Output
- **WHEN** the Execution Engine attempts to write the ensemble output for a specific `date` that already exists in the `daily_lttd` table
- **THEN** the write MUST update/upsert the existing record rather than creating a duplicate, ensuring a single immutable record per `date`.

### Requirement: Cross-Layer Data Integrity
The write abstraction MUST strictly enforce the mathematical bounds defined by the Architecture in `pi_final_research_lttd_01.md`: `Final Score` ∈ [-1.0, +1.0] and `Regime` ∈ {'BULL', 'BEAR', 'SIDEWAYS'}. This requirement applies at the daily level.

#### Scenario: Final Score and Regime Bounds Validation
- **WHEN** Layer 5 attempts to persist a daily output
- **THEN** the system MUST throw a validation error or reject the transaction if `final_score` < -1.0 or `final_score` > +1.0, or if `regime` is not one of the explicitly allowed states.

### Requirement: BRK Data Timestamp Integrity
The timestamp used for logging MUST align with the `stamp` field returned from the BRK API (used as `data_as_of`), avoiding Lookahead Bias by strictly using the historical confirmed time instead of the system's current execution time `datetime.now()`. This requirement applies at the daily level.

#### Scenario: Persisting with Correct Timestamp
- **WHEN** the Execution Engine logs a new `daily_lttd` record based on BRK on-chain metrics
- **THEN** the recorded `date` MUST exactly match the `stamp` field from the BRK API response used to compute the `Final Score`.

## Non-Goals
- We are NOT fetching or integrating with the real BRK API in this specification.
- We are NOT building the Layer 1 HMM inference logic that generates the `Regime` states.
- We are NOT implementing the Layer 4 Ensemble Aggregation logic.
