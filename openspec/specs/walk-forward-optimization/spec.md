# walk-forward-optimization Specification

## Purpose
TBD - created by archiving change p05-ensemble-aggregation. Update Purpose after archive.
## Requirements
### Requirement: WFO Pipeline Execution
At the regime level, the system MUST perform Walk-Forward Optimization (WFO). The rolling pipeline MUST train on a 3-year window, validate on a 6-month window, and test on a 6-month out-of-sample window to avoid static overfitting and lookahead bias.

#### Scenario: Rolling Window Advancing
- **GIVEN** historical daily data spanning multiple years
- **WHEN** the WFO pipeline advances to the next step
- **THEN** the training window MUST strictly precede the validation window, which MUST strictly precede the test window
- **THEN** the out-of-sample test score R² MUST be strictly calculable and stored

### Requirement: Combinatorial Purged Cross-Validation (CPCV)
At the regime level, the WFO pipeline MUST apply Combinatorial Purged Cross-Validation (CPCV). The pipeline MUST purge training bars adjacent to the test/validation windows to prevent data leakage and Lookahead Bias, as referenced in `pi_final_research_lttd_01.md`.

#### Scenario: Purging Adjacent Bars
- **GIVEN** a continuous series of daily OHLCV and Technical Indicator data
- **WHEN** CPCV constructs train/validate/test splits
- **THEN** the number of overlapping purged daily bars between train and test boundaries MUST be > 0 (as defined by the purge window size)
- **THEN** the model MUST verify zero lookahead bias by checking that test data does not influence the training fit

### Requirement: Boundary Target Variable Purging
Enforce that the training targets ($y$) do not leak tomorrow's price direction at the boundaries of the training folds.

#### Scenario: WFO Fold boundary label verification
- **GIVEN** a walk-forward optimization split with a training fold index ending at $t_{train}$ and test fold starting at $t_{test}$.
- **WHEN** constructing the target variable $y_t = \text{sign}(\text{close}_{t+1} - \text{close}_t)$.
- **THEN** the target value at $t_{train}$ SHALL NOT leak the close price of $t_{test}$.
- **AND** the training set target vector $y_{\text{train}}$ SHALL drop or purge the last observation at $t_{train}$ to prevent lookahead bias.

