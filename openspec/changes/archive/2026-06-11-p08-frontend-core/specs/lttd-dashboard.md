## ADDED Requirements

### Requirement: Dashboard Layout and State Visualization
The `lttd-dashboard` must serve as the primary user interface to visualize the system state at the daily level. It must display the current Regime, the ensemble Final Score, and the latest individual Indicator Scores.

#### Scenario: Visualizing Daily System State
- **GIVEN** the frontend has successfully fetched the latest execution state from the Layer 6 Hono backend
- **WHEN** the dashboard renders at the daily level
- **THEN** the HMM-inferred Regime (BULL / BEAR / SIDEWAYS) MUST be clearly displayed (Cross-reference: See `pi_final_research_lttd_01.md` for the 3-state HMM specification on log returns + realized vol)
- **AND** the LTTD Final Score MUST be displayed numerically within the range [-1.0, +1.0]
- **AND** the individual causal Technical Indicator and On-Chain Metric Indicator Scores (∈ {-1, +1}) MUST be listed in a metrics widget to allow auditing

### Requirement: Regime Shift Notification
The dashboard must highlight transitions between Regimes at the regime level.

#### Scenario: Detecting Regime Shifts
- **GIVEN** the historical execution state is loaded into the frontend
- **WHEN** the inferred Regime changes compared to the previous day (e.g., from BULL to SIDEWAYS)
- **THEN** the dashboard MUST visually highlight the Regime shift
- **AND** the UI MUST display the timestamp of the transition to support observability into the HMM layer

## Non-Goals
- Real-time websocket streaming (daily execution rows do not require sub-second updates).
- Implementation of quantitative indicator logic or Walk-Forward Optimization (WFO); these remain strictly in Layers 1-5.
- User authentication or multi-tenant user management.
