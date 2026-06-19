## Context

The LTTD (Long-Term Trend Direction) system operates on a strict 100/0 binary sizing model (100% long in Bull regimes, 0% in Bear regimes). While this maximizes upside during extended bull runs, the inevitable lag in the HMM regime detection and momentum ensemble forces the system to endure the initial -40% to -60% crash of a bear market before the signal officially flips to 0%. 

Previous experiments to eliminate this lag using zero-lag indicators caused excessive whipsawing in choppy markets. Additionally, raw on-chain metrics (like STH-MVRV) are unreliable as standalone absolute triggers because macro cycles have diminishing euphoria peaks (e.g., the Nov 2021 top had very low euphoria compared to 2017).

However, the user's secondary system (`quant-btc-valuation-system`) produces a Composite Oscillator that correctly normalizes tops across all cycles to a bounded negative exhaustion value (`<= -1.20`). This design integrates that external API into the LTTD Execution Engine to serve as an independent, overriding "circuit breaker."

## Goals / Non-Goals

**Goals:**
- Fetch daily Composite Oscillator values from `http://localhost:5173/api/composite`.
- Implement a hard override in `src/execution/sizing.py` to force 0% exposure when the composite value hits `<= -1.20`.
- Maintain 0% exposure until the oscillator cools off to `> -0.50` to prevent catching falling knives.
- Reduce maximum historical drawdown to < -40%.

**Non-Goals:**
- We are NOT modifying the HMM regime detection logic (Layer 1).
- We are NOT adding the Composite Oscillator to the momentum feature matrix (Layer 3). It is strictly an execution override.
- We are NOT implementing partial scaling (e.g., 50% exposure). The system remains strictly 100/0.

## Decisions

1. **API Integration Point (Layer 2)**: 
   - *Decision*: Create a lightweight client `src/data/valuation_api_client.py` to fetch data from `http://localhost:5173/api/composite`.
   - *Rationale*: Decouples the LTTD system from the internal database schema of the valuation system. If the valuation system's internal logic changes, as long as the API contract holds, LTTD remains stable.
   - *Alternatives*: Directly reading the valuation SQLite DB. Rejected because it tightly couples the two projects and breaks encapsulation.

2. **Execution Override (Layer 5)**:
   - *Decision*: Inject the composite value into `src/execution/sizing.py`. The `calculate_target_exposure` function will first check the circuit breaker state before evaluating the HMM regime.
   - *Rationale*: Placing this in Layer 5 ensures that the underlying feature data and HMM probabilities remain uncorrupted by the override. The system still "knows" it is technically in a BULL regime, but it refuses to allocate capital because of structural exhaustion.

3. **Hysteresis (Cool-off mechanism)**:
   - *Decision*: The circuit breaker engages at `<= -1.20` and disengages at `> -0.50`.
   - *Rationale*: Prevents rapid toggling between 100% and 0% if the oscillator hovers around -1.20. Once the bubble pops, the market needs time to clear leverage.

4. **Fallback Behavior**:
   - *Decision*: If the API is unreachable, the system gracefully degrades to standard LTTD logic (ignores the circuit breaker) and logs a warning.
   - *Rationale*: We cannot halt trading entirely if the valuation API goes down temporarily.

## Risks / Trade-offs

- **Risk: Missing a secondary leg up** → If the composite drops below -1.20 but the market continues to rally (e.g., a "blow-off top" extends longer than expected), the system will sit in cash while the market climbs. 
  - *Mitigation*: We accept this trade-off. The goal of this system is wealth preservation at structural extremes. Missing the final 10% of a bubble is vastly preferable to eating a 70% drawdown.
- **Risk: API Downtime** → The valuation API is down during a critical crash.
  - *Mitigation*: The LTTD system will fall back to its native HMM/Momentum logic. It will still eventually exit the market, just with the standard lag. We can also add alert monitoring for API failures.
