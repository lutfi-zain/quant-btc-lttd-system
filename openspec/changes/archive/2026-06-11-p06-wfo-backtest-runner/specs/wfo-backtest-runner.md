## Non-Goals
- Real-time live execution or live database writes (handled by Layer 5: Execution Engine).
- Introducing new Technical Indicators or On-Chain Metrics.
- Modifying PCA Orthogonalization or VIF constraints.

## ADDED Requirements

### Requirement: Walk-Forward Optimization (WFO) Rolling Windows
At the daily level, the backtest runner must slide a training window and testing window across the historical dataset. The training window is 3 years, the validation window is 6 months, and the testing window is 6 months. (Cross-reference: `pi_final_research_lttd_01.md` WFO architecture section).

#### Scenario: Advancing the WFO rolling window
- **GIVEN** a historical dataset of daily OHLCV and BRK On-Chain Metrics
- **WHEN** the Ensemble Model completes training on a 3-year window and testing on the subsequent 6-month out-of-sample window
- **THEN** the runner SHALL slide the training window forward by 6 months and begin the next iteration.

### Requirement: Combinatorial Purged Cross-Validation (CPCV)
At the bar level, the runner must purge training bars adjacent to the test window to mathematically isolate training data from test data and prevent serial correlation leakage, as mathematically specified in `pi_final_research_lttd_01.md`.

#### Scenario: Purging adjacent training bars
- **GIVEN** a 3-year training window and a 6-month test window
- **WHEN** the training set is prepared for the Ensemble Model fit
- **THEN** the runner SHALL drop N days (equal to the maximum indicator lookback, up to 350 days for OU Half-Life) from the training set immediately preceding the test set to ensure 0% leakage.

### Requirement: Historical Simulation Adapter
At the daily level, the runner must feed the Final Score and Regime state into a simulated execution environment to assess historical performance without polluting the live environment.

#### Scenario: Emitting daily signals during simulation
- **GIVEN** the WFO backtest runner is active
- **WHEN** Layer 4 (Ensemble Aggregation) outputs a Final Score ∈ [-1.0, +1.0] and Layer 1 outputs a Regime (Bull / Bear / Sideways)
- **THEN** Layer 5 (Execution Engine) SHALL intercept the output into a simulated portfolio state instead of writing to the live SQLite WAL database.
