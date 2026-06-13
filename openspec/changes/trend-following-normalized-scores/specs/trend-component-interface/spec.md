## ADDED Requirements

### Requirement: TrendComponent base class output
The system SHALL provide a `TrendComponent` abstract base class that all signal components inherit from. The `compute()` method SHALL return a `pd.Series` with values ∈ [0, 1] representing confidence scores.

#### Scenario: Component outputs valid confidence score
- **WHEN** a `TrendComponent` subclass calls `compute(data)` with valid OHLCV DataFrame
- **THEN** the returned `pd.Series` SHALL contain only values ≥ 0.0 and ≤ 1.0
- **AND** the returned `pd.Series` SHALL have the same index as the input DataFrame

#### Scenario: Component with no data returns empty series
- **WHEN** a `TrendComponent` subclass calls `compute(data)` with empty DataFrame
- **THEN** the returned `pd.Series` SHALL be empty with matching index

### Requirement: TrendComponent configurable thresholds
The system SHALL allow each `TrendComponent` to have independently configurable `buy_threshold` and `sell_threshold` parameters. Default values SHALL be `buy_threshold=0.6` and `sell_threshold=0.4`.

#### Scenario: Default thresholds are set correctly
- **WHEN** a `TrendComponent` is instantiated without specifying thresholds
- **THEN** `buy_threshold` SHALL be 0.6
- **AND** `sell_threshold` SHALL be 0.4

#### Scenario: Custom thresholds are applied
- **WHEN** a `TrendComponent` is instantiated with `buy_threshold=0.7` and `sell_threshold=0.3`
- **THEN** the instance SHALL have `buy_threshold=0.7` and `sell_threshold=0.3`

### Requirement: TrendComponent signal generation
The system SHALL provide a `signal()` method on `TrendComponent` that converts confidence scores ∈ [0, 1] to directional signals ∈ {-1.0, 0.0, +1.0} based on threshold comparison.

#### Scenario: Score above buy threshold generates BUY signal
- **WHEN** `signal()` is called with scores where `score >= buy_threshold`
- **THEN** the returned signal SHALL be 1.0 (BUY)

#### Scenario: Score below sell threshold generates SELL signal
- **WHEN** `signal()` is called with scores where `score <= sell_threshold`
- **THEN** the returned signal SHALL be -1.0 (SELL)

#### Scenario: Score between thresholds generates HOLD signal
- **WHEN** `signal()` is called with scores where `sell_threshold < score < buy_threshold`
- **THEN** the returned signal SHALL be 0.0 (HOLD)

### Requirement: TrendComponent causality enforcement
The system SHALL enforce that `TrendComponent.compute()` implementations only access current and historical data (indices ≤ t). No future data access SHALL be permitted.

#### Scenario: Causal filter test passes
- **WHEN** a `TrendComponent` subclass is tested with the `test_no_lookahead` validation
- **THEN** the indicator value at time t SHALL NOT change when future bars t+1..t+N are appended to the input DataFrame
