## MODIFIED Requirements

### Requirement: 5-State Regime Classification via Posterior Thresholding
The system SHALL classify market regimes into 5 states ("Strong Bull", "Weak Bull", "Neutral", "Weak Bear", "Strong Bear") using posterior probability thresholds from the existing 3-state HMM. The HMM n_components SHALL remain at 3; the 5-state classification is derived from threshold logic.

#### Scenario: Strong Bull classification
- **GIVEN** a trained 3-state HMM with posteriors {BULL: 0.85, BEAR: 0.10, SIDEWAYS: 0.05}
- **WHEN** the regime classification logic is executed
- **THEN** the regime SHALL be "Strong Bull" since P(BULL) > 0.70

#### Scenario: Weak Bull classification
- **GIVEN** a trained 3-state HMM with posteriors {BULL: 0.55, BEAR: 0.25, SIDEWAYS: 0.20}
- **WHEN** the regime classification logic is executed
- **THEN** the regime SHALL be "Weak Bull" since 0.40 < P(BULL) ≤ 0.70

#### Scenario: Neutral classification
- **GIVEN** a trained 3-state HMM with posteriors {BULL: 0.35, BEAR: 0.35, SIDEWAYS: 0.30}
- **WHEN** the regime classification logic is executed
- **THEN** the regime SHALL be "Neutral" since no posterior exceeds 0.40

#### Scenario: Weak Bear classification
- **GIVEN** a trained 3-state HMM with posteriors {BULL: 0.20, BEAR: 0.55, SIDEWAYS: 0.25}
- **WHEN** the regime classification logic is executed
- **THEN** the regime SHALL be "Weak Bear" since 0.40 < P(BEAR) ≤ 0.70

#### Scenario: Strong Bear classification
- **GIVEN** a trained 3-state HMM with posteriors {BULL: 0.10, BEAR: 0.85, SIDEWAYS: 0.05}
- **WHEN** the regime classification logic is executed
- **THEN** the regime SHALL be "Strong Bear" since P(BEAR) > 0.70

### Requirement: Regime confidence score
The system SHALL return a confidence score ∈ [0, 1] alongside the regime label, representing the maximum posterior probability across all HMM states.

#### Scenario: High confidence regime
- **GIVEN** HMM posteriors {BULL: 0.90, BEAR: 0.08, SIDEWAYS: 0.02}
- **WHEN** regime classification is executed
- **THEN** the confidence SHALL be 0.90 (max posterior)

#### Scenario: Low confidence regime
- **GIVEN** HMM posteriors {BULL: 0.38, BEAR: 0.35, SIDEWAYS: 0.27}
- **WHEN** regime classification is executed
- **THEN** the confidence SHALL be 0.38 (max posterior)

## REMOVED Requirements

### Requirement: 3-State HMM Training Pipeline
**Reason**: The HMM remains 3-state, but the output classification is now 5-state via posterior thresholding. The requirement for "exactly 3 hidden states representing BULL, BEAR, and SIDEWAYS" is retained but the classification logic is superseded by the new 5-state requirement.
**Migration**: The 3-state HMM training remains unchanged. The new 5-state classification requirement replaces the 3-state classification logic.

### Requirement: HMM Inference and Posterior Probabilities (partial)
**Reason**: The original requirement specified classification when P(Bull) > 0.70 as BULL. This is now part of the 5-state classification logic.
**Migration**: Use the new 5-state classification requirements which include the P(Bull) > 0.70 → Strong Bull mapping.
