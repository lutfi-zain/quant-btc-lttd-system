## Context

The Long-Term Trend Direction (LTTD) system aims to classify Bitcoin's macro directional bias over a 120-350 day horizon using a 6-layer architecture. A critical research finding (`pi_final_research_lttd_01.md`) identified that the legacy Pine Script implementation relied on symmetric smoothing techniques (specifically a Savitzky-Golay Filter) that introduced severe lookahead bias. Such centered windows implicitly reference future data points, creating a "zero-lag" illusion in backtests that is mathematically impossible to replicate in live trading.

To prevent this fatal flaw in the new Python-based architecture, Layer 2 (Signal Engine) requires an abstract structural foundation. This foundation must mathematically guarantee that all technical indicators are strictly causal—processing only current and historical observations ($t, t-1, \dots$). This ensures backtest integrity and guarantees that live execution precisely matches Walk-Forward Optimization (WFO) historical results.

## Goals / Non-Goals

**Goals:**
- Define a `CausalFilter` abstract base class that establishes the contract for all technical indicators in the Signal Engine layer.
- Enforce strict causality to eliminate lookahead bias (i.e., no symmetric windows or future index referencing).
- Establish a programmatic verification utility (`test_no_lookahead()`) to validate causality at the unit test level.
- Ensure all indicator outputs standardize to an Indicator Score ∈ {-1, +1} at the bar level.

**Non-Goals:**
- Implementation of concrete technical indicators (e.g., Kalman RSI, FDI, Supertrend).
- Resolution of multicollinearity (VIF > 10) or Principal Component Analysis (which are strictly scoped to Layer 3: Feature Processing).
- On-chain metric ingestion or API implementations.
- Moving average parameter tuning or Walk-Forward Optimization logic.

## Decisions

### 1. Abstract Base Class (`CausalFilter`)
**Decision:** All OHLCV-derived Technical Indicators will inherit from a Python `abc.ABC` named `CausalFilter`.
**Rationale:** Enforces a unified interface (`compute(data: pd.DataFrame) -> pd.Series`) and type hints across all signals. It establishes an explicit architectural boundary for Layer 2.
**Alternatives Considered:** Duck typing or functional programming patterns. Rejected because an abstract base class natively supports shared testing logic and explicitly documents the causal contract.

### 2. Algorithmic Guardrails on `scipy.signal`
**Decision:** Restrict the use of signal processing libraries exclusively to causal topologies (e.g., IIR/FIR filters without centered windows). Specifically, prohibit the use of `scipy.signal.savgol_filter` or zero-phase filtering (`scipy.signal.filtfilt`).
**Rationale:** `filtfilt` and `savgol_filter` apply forward and backward passes or centered polynomials, referencing future observations and creating lookahead bias. We must rely solely on standard `lfilter` or inherently causal calculations.
**Alternatives Considered:** Custom rewriting of all filters from scratch in NumPy. Rejected because `scipy.signal` is highly optimized in C; we just need to restrict its usage to causal functions.

### 3. Programmatic Lookahead Verification (`test_no_lookahead`)
**Decision:** Implement a reusable test utility that compares indicator outputs on a truncated time-series vs. the same series extended with future data.
**Rationale:** Human code review might miss subtle array indexing errors. A computational proof guarantees that appending data points $t+1 \dots t+N$ does not mathematically alter the historical Indicator Score computed at bar $t$.
**Alternatives Considered:** Relying strictly on cross-validation or out-of-sample backtest degradation. Rejected because unit-level verification catches the error instantly during CI/CD before any backtest is run.

## Risks / Trade-offs

- **[Risk] Increased Drawdown in Backtests:** Eliminating lookahead bias replaces the "zero-lag" illusion with realistic phase delay, inevitably reducing the backtest Sharpe ratio and increasing max drawdown.
  - **Mitigation:** Communicate to stakeholders that this drop represents realism, not a degradation of the model. Historical "perfect" timing was a statistical artifact.
- **[Risk] Developer Friction:** Future quant developers might attempt to use `savgol_filter` or similar symmetric smoothing techniques for prettier curves, failing tests.
  - **Mitigation:** The `test_no_lookahead()` suite acts as a hard CI/CD blocker, and docstrings will explicitly reference the `pi_final_research_lttd_01.md` mathematical proofs.

## Migration Plan

1. **Deploy:** Commit the `CausalFilter` abstract base class and `test_no_lookahead` utility to the `src/signals/` directory structure.
2. **Rollout:** Any newly implemented Technical Indicator in the Signal Engine layer must inherit from this class and pass the lookahead test before merging.
3. **Rollback Strategy:** None required, as this is a foundational architectural addition and does not modify or replace existing execution logic.

## Open Questions

- Should the `CausalFilter` base class handle NaN propagation automatically at the start of the time series, or should concrete indicators manage their own warmup periods?
- Do we need a standardized mechanism within `CausalFilter` to cache intermediate computations for live (tick-level or bar-close) updates, or is full-series recalculation sufficient for daily data?
