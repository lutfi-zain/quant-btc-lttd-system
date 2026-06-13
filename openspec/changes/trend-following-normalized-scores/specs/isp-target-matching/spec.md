## ADDED Requirements

### Requirement: ISP signal timing alignment
The system SHALL produce buy/sell signals that align with ISP signal timing. The alignment metric SHALL measure the percentage of ISP trading dates where the system produces the same action (BUY/SELL/HOLD).

#### Scenario: System matches ISP BUY signals
- **WHEN** the ISP signals CSV contains a BUY action on date D
- **THEN** the system SHALL also produce a BUY signal on date D or within ±3 trading days

#### Scenario: System matches ISP SELL signals
- **WHEN** the ISP signals CSV contains a SELL action on date D
- **THEN** the system SHALL also produce a SELL signal on date D or within ±3 trading days

#### Scenario: Alignment accuracy meets threshold
- **WHEN** the system is backtested against ISP signals CSV (2015-2025)
- **THEN** the signal timing alignment SHALL be ≥80%

### Requirement: ISP position sizing match
The system SHALL produce position sizes that match ISP equity percentages: 0% (no position), 50% (half position), 100% (full position).

#### Scenario: Position sizing matches ISP pattern
- **WHEN** the ISP signals CSV shows `EquityPct=50` on date D
- **THEN** the system SHALL hold 50% of equity in BTC on date D

#### Scenario: Position sizing at zero
- **WHEN** the ISP signals CSV shows `EquityPct=0` on date D
- **THEN** the system SHALL hold 0% of equity in BTC (all cash)

### Requirement: ISP regime transition matching
The system SHALL detect regime transitions that align with ISP regime changes. The transition timing SHALL match within ±5 trading days.

#### Scenario: Regime transition alignment
- **WHEN** the ISP regimes CSV shows a regime change on date D
- **THEN** the system SHALL detect the same regime transition on date D or within ±5 trading days

#### Scenario: Regime label matching
- **WHEN** the system detects a regime transition at date D
- **THEN** the regime label SHALL match the ISP regime label at date D

### Requirement: Backtest validation against ISP
The system SHALL provide a validation function that compares backtest results against ISP CSV files and reports alignment metrics.

#### Scenario: Validation function returns alignment report
- **WHEN** `validate_against_isp(backtest_results, isp_signals_csv, isp_regimes_csv)` is called
- **THEN** the function SHALL return a dictionary containing: `signal_alignment_pct`, `regime_alignment_pct`, `position_sizing_mse`, `total_trades`

#### Scenario: Validation fails if alignment below threshold
- **WHEN** the validation function is called and `signal_alignment_pct < 0.80`
- **THEN** the function SHALL raise a `ValidationWarning` with the alignment percentage

### Requirement: ISP equity curve reproduction
The system SHALL reproduce an equity curve that closely tracks the ISP equity curve. The correlation between system equity and ISP equity SHALL be ≥0.90.

#### Scenario: Equity curve correlation
- **WHEN** the system is backtested against the same data as ISP
- **THEN** the Pearson correlation between system equity curve and ISP equity curve SHALL be ≥0.90
