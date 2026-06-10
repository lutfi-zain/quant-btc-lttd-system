# Walk-Forward Optimization

## Non-Goals
- Generating the Final Score for real-time live trading out of the execution engine.
- Fetching On-Chain Metrics directly from the BRK API.
- Defining the underlying signal computations or technical indicators.

## ADDED Requirements

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
