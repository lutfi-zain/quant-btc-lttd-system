## ADDED Requirements

### Requirement: Conviction-weighted position sizing

The execution engine SHALL compute target exposure based on the absolute value of the final_score (conviction) and realized volatility. The exposure SHALL scale continuously from 0.3 to 1.0 based on conviction.

#### Scenario: High conviction sizing

- **WHEN** `final_score = 0.9` and `vol = 0.3`
- **THEN** `target_exposure` SHALL be approximately 0.95

#### Scenario: Low conviction sizing

- **WHEN** `final_score = 0.2` and `vol = 0.3`
- **THEN** `target_exposure` SHALL be approximately 0.55

#### Scenario: High volatility reduction

- **WHEN** `final_score = 0.9` and `vol = 0.7`
- **THEN** `target_exposure` SHALL be approximately 0.65 (reduced due to high vol)

### Requirement: Exposure bounds

The target exposure SHALL be bounded between 0.3 (minimum) and 1.0 (maximum). The system SHALL NOT use leverage > 1.0x.

#### Scenario: Minimum exposure

- **WHEN** conviction is near zero and volatility is high
- **THEN** `target_exposure` SHALL be at least 0.3

#### Scenario: Maximum exposure

- **WHEN** conviction is maximum and volatility is low
- **THEN** `target_exposure` SHALL be at most 1.0

### Requirement: Exposure smoothing

The target exposure SHALL be smoothed using a 5-day EMA to prevent erratic position changes.

#### Scenario: Exposure smoothing

- **WHEN** the pipeline computes `target_exposure` for date `t`
- **THEN** the actual exposure SHALL be `EMA(target_exposure, span=5)`
- **AND** the exposure SHALL not change by more than 0.2 in a single day

#### Scenario: Smoothing prevents whipsaw

- **WHEN** the final_score oscillates between 0.6 and 0.8 over 5 days
- **THEN** the exposure SHALL remain relatively stable (not oscillate between 0.8 and 0.95)

### Requirement: Volatility-adjusted sizing formula

The exposure formula SHALL be: `base_exposure = 0.5 + 0.5 * |final_score|`, `vol_scalar = max(0.3, 1.0 - vol / 0.8)`, `target_exposure = base_exposure * vol_scalar`.

#### Scenario: Formula validation

- **WHEN** `final_score = 0.5` and `vol = 0.4`
- **THEN** `base_exposure = 0.5 + 0.5 * 0.5 = 0.75`
- **AND** `vol_scalar = max(0.3, 1.0 - 0.4/0.8) = 0.5`
- **AND** `target_exposure = 0.75 * 0.5 = 0.375`
- **AND** after EMA smoothing, the exposure SHALL be approximately 0.4

## MODIFIED Requirements

### Requirement: Sizing function uses final_score

The `calculate_target_exposure()` function SHALL use the `final_score` parameter to compute exposure. The `regime` parameter SHALL be used for display purposes only (not for sizing).

#### Scenario: Sizing with final_score

- **WHEN** `calculate_target_exposure(final_score=0.8, regime="Strong Bull")` is called
- **THEN** the output SHALL be based on `final_score=0.8`
- **AND** the output SHALL NOT be a fixed value based on regime name

#### Scenario: Regime for display only

- **WHEN** the execution engine logs the trade
- **THEN** the regime name SHALL be included in the log
- **AND** the regime name SHALL NOT determine the exposure

### Requirement: No binary in/out sizing

The system SHALL NOT use binary exposure (0.0 or 1.0-1.5). The exposure SHALL be a continuous value between 0.3 and 1.0.

#### Scenario: Continuous exposure

- **WHEN** the pipeline runs on any date
- **THEN** `target_exposure` SHALL be a float between 0.3 and 1.0
- **AND** `target_exposure` SHALL NOT be exactly 0.0 (except for the first 5 days during EMA warmup)
