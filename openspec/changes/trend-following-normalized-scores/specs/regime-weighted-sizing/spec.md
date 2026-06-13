## MODIFIED Requirements

### Requirement: 5-State Regime Position Sizing
The Execution Engine SHALL compute target BTC exposure ∈ {0.0, 0.5, 1.0} based on the 5-state regime classification and coherence signal. Position sizing SHALL follow the ISP pattern: Weak Bull entry (50%), Strong Bull add (100%), Weak Bull exit (50%), Neutral exit (0%).

#### Scenario: Weak Bull + BUY coherence → 50% position
- **GIVEN** a coherence signal of 1.0 (BUY) and regime "Weak Bull"
- **WHEN** the execution engine computes target exposure
- **THEN** the target exposure SHALL be 0.5 (50% of equity in BTC)

#### Scenario: Strong Bull + BUY coherence → 100% position
- **GIVEN** a coherence signal of 1.0 (BUY) and regime "Strong Bull"
- **WHEN** the execution engine computes target exposure
- **THEN** the target exposure SHALL be 1.0 (100% of equity in BTC)

#### Scenario: Weak Bull + SELL coherence → 50% position
- **GIVEN** a coherence signal of -1.0 (SELL) and regime "Weak Bull"
- **WHEN** the execution engine computes target exposure
- **THEN** the target exposure SHALL be 0.5 if current exposure > 0.5, else 0.0

#### Scenario: Neutral + SELL coherence → 0% position
- **GIVEN** a coherence signal of -1.0 (SELL) and regime "Neutral"
- **WHEN** the execution engine computes target exposure
- **THEN** the target exposure SHALL be 0.0 (all cash)

#### Scenario: Weak Bear/Strong Bear → 0% position
- **GIVEN** regime "Weak Bear" or "Strong Bear"
- **WHEN** the execution engine computes target exposure
- **THEN** the target exposure SHALL be 0.0 regardless of coherence signal

### Requirement: Discrete Position Sizing
Position sizing SHALL use discrete values {0.0, 0.5, 1.0} rather than continuous scaling. This matches ISP pattern and reduces execution complexity.

#### Scenario: Position transitions are discrete
- **GIVEN** any combination of regime and coherence signal
- **WHEN** the execution engine computes target exposure
- **THEN** the exposure MUST be exactly 0.0, 0.5, or 1.0 (no intermediate values)

### Requirement: ISP Equity Percentage Match
The system SHALL produce position sizes that match ISP equity percentages exactly. The Mean Squared Error between system exposure and ISP EquityPct/100 SHALL be < 0.01.

#### Scenario: Position sizing matches ISP
- **GIVEN** historical ISP signals with EquityPct column
- **WHEN** the system is backtested over the same period
- **THEN** the MSE between system exposure and ISP EquityPct/100 SHALL be < 0.01

## REMOVED Requirements

### Requirement: Regime-weighted position sizing (continuous)
**Reason**: Replaced by discrete 5-state regime sizing. Continuous scaling based on Final Score is incompatible with ISP's discrete 50%/100%/0% pattern.
**Migration**: Use discrete position sizing based on regime + coherence signal as defined in the new requirements above.

## RENAMED Requirements

### Requirement: Regime-weighted position sizing → 5-State Regime Position Sizing
FROM: "Regime-weighted position sizing"
TO: "5-State Regime Position Sizing"
