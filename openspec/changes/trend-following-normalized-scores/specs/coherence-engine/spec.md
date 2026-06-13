## ADDED Requirements

### Requirement: CoherenceEngine majority voting
The system SHALL provide a `CoherenceEngine` class that evaluates agreement across multiple component signals. The default mode SHALL be "majority" requiring ≥50%+1 components to agree.

#### Scenario: Majority agreement produces coherent BUY signal
- **WHEN** `CoherenceEngine.evaluate()` is called with 6 component signals where 4 vote BUY (1.0)
- **THEN** the `coherence_signal` SHALL be 1.0 (BUY)
- **AND** the `confidence` SHALL be 4/6 ≈ 0.667

#### Scenario: Majority agreement produces coherent SELL signal
- **WHEN** `CoherenceEngine.evaluate()` is called with 6 component signals where 4 vote SELL (-1.0)
- **THEN** the `coherence_signal` SHALL be -1.0 (SELL)
- **AND** the `confidence` SHALL be 4/6 ≈ 0.667

#### Scenario: No majority produces HOLD signal
- **WHEN** `CoherenceEngine.evaluate()` is called with 6 component signals where 3 vote BUY and 3 vote SELL
- **THEN** the `coherence_signal` SHALL be 0.0 (HOLD)

### Requirement: CoherenceEngine configurable agreement modes
The system SHALL support three agreement modes: "majority" (50%+1), "supermajority" (75%+1), and "unanimous" (100%).

#### Scenario: Supermajority mode requires 75% agreement
- **WHEN** `CoherenceEngine` is instantiated with `mode="supermajority"` and evaluates 6 components
- **THEN** the required agreement SHALL be 5 components (int(6 * 0.75) + 1)

#### Scenario: Unanimous mode requires 100% agreement
- **WHEN** `CoherenceEngine` is instantiated with `mode="unanimous"` and evaluates 6 components
- **THEN** the required agreement SHALL be 6 components

#### Scenario: Custom min_agreement overrides mode
- **WHEN** `CoherenceEngine` is instantiated with `min_agreement=3` and `mode="supermajority"`
- **THEN** the required agreement SHALL be 3 (min_agreement takes precedence)

### Requirement: CoherenceEngine returns voting statistics
The system SHALL return detailed voting statistics including `buy_votes`, `sell_votes`, `total_components`, `coherence_signal`, and `confidence` for each bar.

#### Scenario: Voting statistics are returned correctly
- **WHEN** `CoherenceEngine.evaluate()` is called with 6 components (4 BUY, 1 SELL, 1 HOLD)
- **THEN** the returned DataFrame SHALL contain columns: `buy_votes=4`, `sell_votes=1`, `total_components=6`, `coherence_signal=1.0`, `confidence=0.667`

### Requirement: CoherenceEngine regime-aware evaluation
The system SHALL accept a `regime` parameter in `evaluate()` to enable regime-specific coherence logic in future iterations.

#### Scenario: Regime parameter is accepted
- **WHEN** `CoherenceEngine.evaluate()` is called with `regime="Weak Bull"`
- **THEN** the method SHALL execute without error and return valid coherence results
