# regime-weighted-sizing Specification

## Purpose
TBD - created by archiving change p06-execution-engine. Update Purpose after archive.

## Requirements

### Requirement: Binary Hysteresis Position Sizing
The execution engine MUST calculate target BTC exposure as a strict binary state (either 0.0 or 1.0). To prevent whipsaws and optimize trade entry/exit, it MUST use asymmetric entry/exit thresholds with hysteresis on smoothed ensemble scores.
*   **Entry Threshold (`SCORE_ENTRY`)**: The system SHALL enter a long position (exposure = 1.0) when the smoothed entry score is `>= 0.32039808689747296`.
*   **Exit Threshold (`SCORE_EXIT`)**: The system SHALL exit the long position (exposure = 0.0) when the smoothed exit score is `<= 0.3109636587111976`.

#### Scenario: Entry trigger with hysteresis
- **GIVEN** the system is currently OUT of position (exposure = 0.0)
- **WHEN** the smoothed entry score rises to `>= 0.32039808689747296`
- **THEN** target exposure MUST become `1.0`.

#### Scenario: Exit trigger with hysteresis
- **GIVEN** the system is currently IN position (exposure = 1.0)
- **WHEN** the smoothed exit score drops to `<= 0.3109636587111976`
- **THEN** target exposure MUST become `0.0`.

### Requirement: Score Smoothing via SuperSmoother
The raw ensemble scores MUST be smoothed using John Ehlers' 2-pole SuperSmoother filter before applying threshold checks, to minimize high-frequency noise.
*   **Entry Smooth Period**: 7 days.
*   **Exit Smooth Period**: 5 days.

### Requirement: Re-entry Cool-off (RCO) and Minimum Holding Period (MHP)
To prevent rapid switching of positions on short-lived noise:
*   **Re-entry Cool-off (RCO)**: After an exit, the system MUST wait at least `1` day before entering a new position.
*   **Minimum Holding Period (MHP)**: After an entry, the system MUST hold the position for at least `12` days before allowing an exit.

#### Scenario: Minimum Holding Period enforcement
- **GIVEN** a position was entered less than `12` days ago
- **WHEN** the exit score drops below `SCORE_EXIT`
- **THEN** the system MUST keep exposure at `1.0`.

#### Scenario: Re-entry Cool-off enforcement
- **GIVEN** a position was exited `0` days ago (today)
- **WHEN** the entry score rises above `SCORE_ENTRY`
- **THEN** the system MUST keep exposure at `0.0`.

### Requirement: Trend-Following Moving Average Filter
The system MUST implement a causal long-term Moving Average filter to prevent trade entries when BTC price is below its moving average, confirming the macro trend direction.
*   **MA Period**: `156` days.
*   **Condition**: Trade entry is only permitted if the daily close price is strictly greater than the 156-day Moving Average.

#### Scenario: Entry blocked by MA Filter
- **GIVEN** the entry score is `>= 0.32039808689747296` and RCO is satisfied
- **WHEN** the BTC close price is `<= 156-day MA`
- **THEN** the system MUST remain OUT (exposure = 0.0).

### Requirement: No lookahead bias in sizing
The position sizing logic SHALL NOT use any future data points. All decisions MUST be made using causal filters and past observations.
