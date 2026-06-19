## Why

The current LTTD system (baseline: ~49% CAGR, -71% Max DD) suffers massive drawdowns during Bull market crashes (up to -75.77% Max DD). This is primarily driven by the strict 100/0 Binary Sizing combined with the necessary lag of our HMM regime detection and momentum ensemble. While binary sizing captures the full upside of bull runs, it forces the system to endure the entire brunt of a crash before the signal flips. 

Previous attempts to solve this via zero-lag indicators led to whipsawing that degraded performance (41% CAGR). Furthermore, on-chain metrics like STH-MVRV and STH-NUPL alone failed to catch the November 2021 "Double Top", as euphoria thresholds shrink iteratively over macro cycles.

However, the `quant-btc-valuation-system` provides a "Composite Oscillator" that elegantly normalizes macro tops across all cycles (2017, 2021 Spring, 2021 Fall, 2024 Spring) to a bounded negative exhaustion value (`<= -1.20`). By using this external mathematical composite as a circuit breaker, we can systematically cut exposure to 0% at macro tops *before* the price action breaks down, sidestepping severe drawdowns without adding noisy zero-lag signals to our feature matrix.

## What Changes

1. **Valuation API Integration (Layer 2 & Layer 5)**: We will integrate the LTTD system with the existing `quant-btc-valuation-system` via its local REST API (`http://localhost:5173/api/composite`).
2. **Hard Circuit Breaker Override (Layer 5)**: We will update the Sizing engine. If the `composite_value <= -1.20` (Extreme Overvaluation / Euphoria), the Execution Engine will trigger a hard stop, forcing `target_exposure = 0.0` regardless of the HMM regime or Ensemble score. 
3. **Cool-off Logic (Layer 5)**: The exposure remains at 0% until the composite oscillator cools down to a safer structural level (e.g., `> -0.50`), at which point the normal ensemble logic resumes.

## Capabilities

### New Capabilities
- `valuation-api-client`: Integration to fetch daily Composite Oscillator values from the `quant-btc-valuation-system` API.
- `composite-circuit-breaker`: Hard stop sizing rules driven by the Composite Oscillator to exit overheated markets.

### Modified Capabilities
- `exposure-sizing`: The exposure sizing logic in Layer 5 will be overridden by the external composite value during bubble phases.

## Impact

- **Affected Layers**: Layer 2 (Signal Engine / Data Ingestion) and Layer 5 (Execution Engine Sizing).
- **Backtest Impact**: By dodging the absolute tops of 2017, Spring 2021, Fall 2021, and Spring 2024, we estimate a dramatic reduction in Max Drawdown (targeting < -40%) and an increase in CAGR that beats Buy & Hold (> 60%), without sacrificing the stability of our momentum indicators.
- **Data Dependencies**: This introduces a NEW data dependency: the local API endpoint `http://localhost:5173/api/composite` hosted by the `quant-btc-valuation-system`.
- **Feature Redundancy**: The Composite Oscillator is purely used as an execution override in Layer 5, NOT as an indicator in the Feature Matrix (Layer 3). Therefore, it does not inflate VIF or break the orthogonal PCA assumption.
