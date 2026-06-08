## Non-Goals
- Re-calculating HMM probabilities in the frontend.
- Displaying sub-daily regime fluctuations.

## ADDED Requirements

### Requirement: Render HMM Posterior Probabilities
The regime-probability-panel SHALL display the posterior probabilities for the three HMM states (BULL, BEAR, SIDEWAYS) at the daily level. The visualization MUST explicitly show that the sum of the probabilities equals 1.0, reflecting the Regime Detection layer outputs as verified in the structural research (see pi_final_research_lttd_01.md for 3-state HMM definitions).

#### Scenario: Visualizing dominant Regime probability
- **WHEN** the regime-probability-panel receives daily state probability data
- **THEN** the panel MUST display the three Regime probabilities where $P(\text{Bull}) + P(\text{Bear}) + P(\text{Sideways}) = 1.0$ at the daily level
- **THEN** the UI MUST explicitly highlight the dominant Regime (the state with the highest probability $> 0.50$, if applicable) for the current 120-350 day epoch
