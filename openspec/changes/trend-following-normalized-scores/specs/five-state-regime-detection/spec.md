## ADDED Requirements

### Requirement: 5-state regime classification
The system SHALL classify market regimes into 5 states: "Strong Bull", "Weak Bull", "Neutral", "Weak Bear", "Strong Bear" using posterior probability thresholds from a 3-state HMM.

#### Scenario: Strong Bull classification
- **WHEN** the HMM posterior probability P(BULL) > 0.70
- **THEN** the regime SHALL be classified as "Strong Bull"

#### Scenario: Weak Bull classification
- **WHEN** the HMM posterior probability P(BULL) > 0.40 and ≤ 0.70
- **THEN** the regime SHALL be classified as "Weak Bull"

#### Scenario: Neutral classification
- **WHEN** no regime posterior exceeds 0.40
- **THEN** the regime SHALL be classified as "Neutral"

#### Scenario: Weak Bear classification
- **WHEN** the HMM posterior probability P(BEAR) > 0.40 and ≤ 0.70
- **THEN** the regime SHALL be classified as "Weak Bear"

#### Scenario: Strong Bear classification
- **WHEN** the HMM posterior probability P(BEAR) > 0.70
- **THEN** the regime SHALL be classified as "Strong Bear"

### Requirement: Regime classification includes confidence
The system SHALL return a confidence score ∈ [0, 1] alongside the regime label, representing the maximum posterior probability across all HMM states.

#### Scenario: Confidence reflects regime certainty
- **WHEN** the HMM returns posteriors {BULL: 0.85, BEAR: 0.10, SIDEWAYS: 0.05}
- **THEN** the regime SHALL be "Strong Bull" with confidence 0.85

#### Scenario: Low confidence regime detection
- **WHEN** the HMM returns posteriors {BULL: 0.38, BEAR: 0.35, SIDEWAYS: 0.27}
- **THEN** the regime SHALL be "Weak Bull" with confidence 0.38

### Requirement: Regime transition logging
The system SHALL log all regime transitions with timestamp, from-regime, to-regime, posterior probabilities, and triggering metrics.

#### Scenario: Regime transition is logged
- **WHEN** the regime changes from "Weak Bull" to "Strong Bull" on bar t
- **THEN** a log entry SHALL be created with format: `[timestamp] REGIME TRANSITION: Weak Bull → Strong Bull (P_bull=0.75, P_bear=0.15, P_sideways=0.10)`

### Requirement: 5-state regime matches ISP classifications
The system SHALL produce regime classifications that match the ISP regimes CSV within acceptable tolerance. The classification accuracy SHALL be ≥70% when compared against ISP ground truth.

#### Scenario: Regime classification matches ISP
- **WHEN** the system processes historical data from 2015-2025
- **THEN** the regime classification accuracy vs ISP CSV SHALL be ≥70%
