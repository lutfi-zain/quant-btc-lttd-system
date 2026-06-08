## Why

Symmetric smoothing techniques (such as the legacy Savitzky-Golay flow bands) incorporate future price data points into their current calculations, introducing severe lookahead bias that invalidates backtest realism and fails in live trading. Establishing a strictly causal abstract base class ensures that all time-series filters mathematically process only current and historical observations ($t, t-1, t-2 \dots$), securing statistical integrity and guaranteeing that live execution precisely matches historical Walk-Forward Optimization (WFO) results.

## What Changes

- **Add `CausalFilter` Base Class**: Introduce an abstract base class for all signal processing algorithms.
- **Enforce Causality Constraints**: Implement algorithmic guardrails that strictly forbid non-causal indices (e.g., symmetric windows) and ensure only past and present values are utilized.
- **Add Lookahead Bias Test Suite**: Introduce a `test_no_lookahead()` utility that computationally verifies indicator values at time $t$ remain invariant when future bars $t+1 \dots t+N$ are introduced.
- **Architectural Boundary Enforcement**: Restrict `scipy.signal` usage to causal filter topologies only (e.g., IIR/FIR without centered windows or zero-phase `filtfilt`).

## Capabilities

### New Capabilities
- `causal-filter-base`: Defines the abstract foundation, causality guarantees, and testing utilities for all signal processing algorithms.

### Modified Capabilities

## Backtest Impact

- **Sharpe Ratio**: Expect a significant but realistic reduction in backtest Sharpe ratio (e.g., from an inflated ~3.5 to a realistic ~1.8) compared to the flawed legacy Pine Script implementation due to the elimination of the "zero-lag" illusion caused by lookahead bias.
- **Max Drawdown**: Max drawdown may increase in backtests, accurately reflecting the inherent lag penalty of causal filters that cannot "see into the future" during sharp market reversals.

## Impact

- **Architecture Layers Affected**: Primarily impacts **Layer 2: Signal Engine**, establishing the standard for all technical indicators.
- **Code & Dependencies**: Relies on `numpy` and `scipy.signal` (restricted to causal functions).
- **Data Dependencies**: No new data dependencies, external APIs, or datasets are introduced; solely operates on the internal OHLCV price vector feed.
- **Redundancy/VIF**: As this is an abstract structural foundation and not a specific new feature vector, VIF redundancy checks apply downstream when concrete indicators subclassing `CausalFilter` are implemented.
