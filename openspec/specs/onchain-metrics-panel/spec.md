# onchain-metrics-panel Specification

## Purpose
TBD - created by archiving change p09-frontend-panels.

## Requirements

### Requirement: Render Causal On-Chain Metrics
The onchain-metrics-panel SHALL display the processed On-Chain Metric signals (e.g., sth_mvrv, sth_nupl, sth_sopr_24h) overlaid with critical thresholds at the daily level. This MUST reflect the output from the Signal Engine's Causal Filter to ensure the absence of Lookahead Bias, consistent with findings in pi_final_research_lttd_01.md regarding cycle top lead-lag behavior.

#### Scenario: Visualizing On-Chain Metric critical thresholds
- **WHEN** the onchain-metrics-panel retrieves daily data for STH-MVRV and STH-NUPL
- **THEN** the panel MUST plot the daily BRK Series values matching the BRK Stamp timestamps exactly
- **THEN** the panel MUST visibly demarcate the specific threshold limits, such as an STH-MVRV value $> 2.0$ or STH-NUPL value $> 0.75$, to identify potential Regime filter activations
