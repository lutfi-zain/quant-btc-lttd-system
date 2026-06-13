## ADDED Requirements

### Requirement: Regime-dependent threshold adjustment
The system SHALL adjust component buy/sell thresholds based on the current regime state. The adjustment SHALL follow the pattern: bull regimes lower buy threshold (easier to buy), bear regimes raise buy threshold (harder to buy).

#### Scenario: Strong Bull regime lowers buy threshold
- **WHEN** the regime is "Strong Bull" and a component has `buy_threshold=0.6`
- **THEN** the adjusted buy threshold SHALL be 0.5 (0.6 - 0.1)

#### Scenario: Strong Bull regime raises sell threshold
- **WHEN** the regime is "Strong Bull" and a component has `sell_threshold=0.4`
- **THEN** the adjusted sell threshold SHALL be 0.5 (0.4 + 0.1)

#### Scenario: Weak Bear regime raises buy threshold
- **WHEN** the regime is "Weak Bear" and a component has `buy_threshold=0.6`
- **THEN** the adjusted buy threshold SHALL be 0.8 (0.6 + 0.2)

#### Scenario: Weak Bear regime lowers sell threshold
- **WHEN** the regime is "Weak Bear" and a component has `sell_threshold=0.4`
- **THEN** the adjusted sell threshold SHALL be 0.2 (0.4 - 0.2)

### Requirement: Threshold adjustment matrix
The system SHALL apply the following adjustment matrix to component thresholds:

| Regime | Buy Adjustment | Sell Adjustment |
|--------|---------------|-----------------|
| Strong Bull | -0.1 | +0.1 |
| Weak Bull | 0.0 | 0.0 |
| Neutral | +0.1 | -0.1 |
| Weak Bear | +0.2 | -0.2 |
| Strong Bear | +0.3 | -0.3 |

#### Scenario: All regime adjustments are applied correctly
- **WHEN** components are evaluated across all 5 regimes
- **THEN** the threshold adjustments SHALL match the matrix above for each regime

### Requirement: Threshold bounds enforcement
The system SHALL clamp adjusted thresholds to the range [0.1, 0.9] to prevent extreme threshold values.

#### Scenario: Upper bound enforcement
- **WHEN** a component has `buy_threshold=0.85` in "Strong Bear" regime (+0.3 adjustment)
- **THEN** the adjusted buy threshold SHALL be 0.9 (clamped from 1.15)

#### Scenario: Lower bound enforcement
- **WHEN** a component has `sell_threshold=0.15` in "Strong Bull" regime (+0.1 adjustment)
- **THEN** the adjusted sell threshold SHALL be 0.1 (clamped from 0.05)

### Requirement: Optional regime adjustment bypass
The system SHALL allow components to disable regime-aware threshold adjustment via `regime_adjusted=False`.

#### Scenario: Regime adjustment disabled
- **WHEN** a component is instantiated with `regime_adjusted=False`
- **THEN** the `signal()` method SHALL use fixed thresholds regardless of regime
