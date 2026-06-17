# indicator-signals Specification

## Purpose
TBD - created by archiving change trend-following-ml-consensus. Update Purpose after archive.
## Requirements
### Requirement: Continuous Indicator Output
The fundamental output contract of all Layer 2 Signal Engine indicators MUST be modified to return continuous intensities rather than discrete votes.

#### Scenario: Layer 2 Signal Output
- **GIVEN** any Technical Indicator or On-Chain Metric evaluated by the Signal Engine
- **WHEN** the `Indicator Score` is calculated for a given day
- **THEN** the value MUST be a continuous float ∈ [0.0, 1.0], replacing the legacy behavior which emitted discrete {-1, +1} integers.

### Requirement: Indicator suite reduced to 4 technical + 4 on-chain

The signal engine SHALL use only 4 technical indicators (TrendStrengthIndex, FourierSupertrend, AdvancedStochastic, FDI) and 4 on-chain metrics (STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit). QuantileDEMA and KalmanRSI SHALL be removed.

#### Scenario: Active indicators

- **WHEN** the signal engine computes indicator scores
- **THEN** only the following indicators SHALL be computed:
  - TrendStrengthIndex
  - FourierSupertrend
  - AdvancedStochastic (periods 1-30)
  - FDI

#### Scenario: Removed indicators

- **WHEN** the signal engine runs
- **THEN** QuantileDEMA SHALL NOT be computed
- **AND** KalmanRSI SHALL NOT be computed (replaced by RSI-50 variant)

### Requirement: FDI VIF resolved

The FDI indicator SHALL remain in the feature matrix. QuantileDEMA (VIF → ∞ with FDI) SHALL be removed instead. The VIF analysis SHALL confirm FDI VIF < 10 after QuantileDEMA removal.

#### Scenario: FDI VIF check

- **WHEN** VIF analysis runs on the feature matrix (without QuantileDEMA)
- **THEN** FDI VIF SHALL be < 10
- **AND** no indicator SHALL have VIF → ∞

#### Scenario: FDI kept for economic reasoning

- **WHEN** VIF analysis compares FDI and QuantileDEMA
- **THEN** FDI SHALL be retained (more principled: fractal dimension analysis)
- **AND** QuantileDEMA SHALL be removed (redundant: percentile bands)

### Requirement: AdvancedStochastic periods reduced

The AdvancedStochastic indicator SHALL compute stochastic oscillator for periods 1-30 only (reduced from 1-129). The output SHALL be the average of 30 binary trend signals.

#### Scenario: Reduced period computation

- **WHEN** AdvancedStochastic computes the indicator score
- **THEN** the stochastic oscillator SHALL be computed for periods 1 through 30
- **AND** the output SHALL be the mean of 30 binary signals
- **AND** periods 31-129 SHALL NOT be computed

#### Scenario: Computational efficiency

- **WHEN** AdvancedStochastic runs with reduced periods
- **THEN** the computation time SHALL be approximately 23% of original (30/129)

### Requirement: TrendStrengthIndex unchanged

The TrendStrengthIndex indicator SHALL remain unchanged. It is the best indicator in the suite (VWMA-ATR distance, volume-weighted price displacement normalized by volatility).

#### Scenario: TrendStrengthIndex preserved

- **WHEN** the signal engine computes TrendStrengthIndex
- **THEN** the VWMA length SHALL be 145 (unchanged)
- **AND** the ATR length SHALL be 50 (unchanged)
- **AND** the crossover thresholds SHALL be enter=1.5, exit=1.0 (unchanged)

### Requirement: FourierSupertrend unchanged

The FourierSupertrend indicator SHALL remain unchanged. The FFT-based adaptive ATR period is conceptually sound.

#### Scenario: FourierSupertrend preserved

- **WHEN** the signal engine computes FourierSupertrend
- **THEN** the FFT window SHALL be 256 bars (unchanged)
- **AND** the ATR period SHALL be adaptive based on dominant frequency

### Requirement: Indicator lag budget compliance

Each indicator SHALL have a maximum effective lag of 100 days. The average indicator lag SHALL be < 50 days.

#### Scenario: Lag measurement

- **WHEN** the signal engine computes all indicator scores
- **THEN** the effective lag of each indicator SHALL be measured
- **AND** TrendStrengthIndex lag ≈ 70 days (within budget)
- **AND** FourierSupertrend lag ≈ 100 days (at budget limit)
- **AND** AdvancedStochastic lag ≈ 30 days (well within budget)
- **AND** FDI lag ≈ 50 days (within budget)

#### Scenario: Average lag compliance

- **WHEN** the signal engine computes all indicator scores
- **THEN** the average indicator lag SHALL be < 50 days
- **AND** no indicator SHALL have lag > 100 days

