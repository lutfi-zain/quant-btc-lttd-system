## ADDED Requirements

### Requirement: Forward return target variable

The system SHALL use 21-day forward log return as the ML training target, replacing the forward-filled ISP regime labels. The target SHALL be z-score normalized using a rolling 252-day window and clipped to [-1, +1].

#### Scenario: Forward return calculation

- **WHEN** the pipeline computes the target variable for date `t`
- **THEN** the target value SHALL be `zscore(log(close[t+21] / close[t]))`, normalized over the trailing 252-day window
- **AND** the value SHALL be clipped to the range [-1, +1]

#### Scenario: No lookahead in target

- **WHEN** the pipeline computes the target for date `t`
- **THEN** the target SHALL only use price data from dates `t` through `t+21`
- **AND** the z-score normalization SHALL only use data from dates `t-252` through `t`

#### Scenario: Target distribution

- **WHEN** the target variable is computed over the full dataset
- **THEN** the distribution SHALL be approximately normal (mean ≈ 0, std ≈ 1)
- **AND** no more than 5% of values SHALL be at the clip boundaries (-1 or +1)

### Requirement: Target variable excludes ISP labels

The system SHALL NOT use the ISP regime labels (`isp-regimes-btcusd-*.csv`) as the ML training target. The ISP labels MAY be retained for presentation and comparison purposes only.

#### Scenario: ISP labels not used in training

- **WHEN** the feature matrix `X_train` is constructed
- **THEN** the target vector `y_train` SHALL be computed from forward returns
- **AND** the ISP regime labels SHALL NOT appear in `y_train`

#### Scenario: ISP labels available for display

- **WHEN** the presentation layer renders regime information
- **THEN** the ISP labels MAY be displayed alongside the model's predictions for comparison

### Requirement: Target variable freshness validation

The system SHALL validate that the target variable is computed using only confirmed (closed) bars. The target for date `t` SHALL NOT be computed until date `t+21` has a confirmed close.

#### Scenario: Real-time target computation

- **WHEN** the pipeline runs on date `t`
- **THEN** the target for date `t-21` SHALL be available (using confirmed close from `t`)
- **AND** the target for date `t` SHALL be `NaN` (future data not yet available)

#### Scenario: Backtest target computation

- **WHEN** the backtest runner processes date `t`
- **THEN** the target for date `t` SHALL use the actual close price from date `t+21`
- **AND** no future information SHALL leak into the training set

## MODIFIED Requirements

### Requirement: Target loader no longer forward-fills

The target loader SHALL compute forward returns directly instead of forward-filling ISP regime labels.

#### Scenario: Target loader output

- **WHEN** `load_regime_targets()` is called
- **THEN** the output SHALL be a pandas Series indexed by date
- **AND** values SHALL be forward returns (not ISP regime intensities)
- **AND** the Series SHALL NOT contain forward-filled constant values

#### Scenario: Target loader data source

- **WHEN** the target loader fetches price data
- **THEN** it SHALL use the same OHLCV data source as the signal engine
- **AND** it SHALL NOT read from `isp-regimes-btcusd-*.csv`
