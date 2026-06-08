## ADDED Requirements

### Requirement: Database Initialization
The system MUST initialize a local SQLite database at `database/lttd.db` and configure it to use Write-Ahead Logging (WAL) mode to support concurrent read/write operations from Layer 5 (Execution Engine) and Layer 6 (Presentation). This requirement applies at the system level.

#### Scenario: Database Creation
- **WHEN** the system starts and `database/lttd.db` does not exist
- **THEN** it MUST create the database file at the specified path and execute `PRAGMA journal_mode=WAL;` to enable concurrent execution.

### Requirement: Schema - Daily LTTD Table
The database MUST contain a `daily_lttd` table to immutably store the daily execution outputs, specifically the macro directional bias (`Regime`) and the weighted ensemble output (`Final Score`). This supports the 5-Layer Pipeline architecture defined in `pi_final_research_lttd_01.md`. This requirement applies at the daily level.

#### Scenario: `daily_lttd` Table Structure
- **WHEN** the database schema is initialized
- **THEN** the `daily_lttd` table MUST exist with columns: `date` (Primary Key, YYYY-MM-DD), `regime` (TEXT, restricted to 'BULL', 'BEAR', 'SIDEWAYS'), `final_score` (REAL, ranging from -1.0 to 1.0), and `created_at` (TIMESTAMP).

### Requirement: Schema - Indicator Scores Table
The database MUST contain an `indicator_scores` table to log the individual causal `Indicator Score`s from Layer 2 (Signal Engine) to track component contributions over time. This requirement applies at the daily level.

#### Scenario: `indicator_scores` Table Structure
- **WHEN** the database schema is initialized
- **THEN** the `indicator_scores` table MUST exist with columns: `date` (YYYY-MM-DD), `indicator_name` (TEXT), `score` (REAL, restricted to {-1, +1} as per `pi_final_research_lttd_01.md`), and a composite Primary Key on (`date`, `indicator_name`).

### Requirement: Schema - Regime Transitions Table
The database MUST contain a `regime_transitions` table to log transitions in the HMM-inferred state, including posterior probabilities and triggering metrics. This requirement applies at the regime level.

#### Scenario: `regime_transitions` Table Structure
- **WHEN** the database schema is initialized
- **THEN** the `regime_transitions` table MUST exist with columns: `transition_date` (YYYY-MM-DD), `previous_regime` (TEXT), `new_regime` (TEXT), `posterior_probability` (REAL), `triggering_metrics` (JSON or TEXT), and `created_at` (TIMESTAMP).

## Non-Goals
- We are NOT implementing the actual execution logic to populate these tables yet.
- We are NOT designing the Presentation Layer (API endpoints) in this spec.
- We are NOT implementing Walk-Forward Optimization (WFO) backtest tables here.
