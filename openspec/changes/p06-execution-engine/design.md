## Context

The trading system evaluates macro directional bias through a rigorous 4-layer quantitative stack: Regime Detection (HMM), Signal Engine (Causal Indicators), Feature Processing (PCA + VIF pruning), and Ensemble Aggregation (L1-Lasso Logistic Regression). However, the system currently lacks Layer 5: Execution Engine. This terminal layer is required to convert the continuous `Final Score` ∈ [-1.0, +1.0] and the categorical HMM `Regime` ∈ {BULL, BEAR, SIDEWAYS} into actionable, statistically scaled target portfolio allocations. The Execution Engine serves as the bridge between the Python ML pipeline and the Presentation layer by persisting its execution decisions to a shared SQLite database.

## Goals / Non-Goals

**Goals:**
- Implement Layer 5: Execution Engine (`src/execution/`) to dynamically map `Final Score` and `Regime` into a target BTC exposure (ranging from 0.0 to 1.0).
- Apply regime-weighted sizing logic to minimize portfolio variance, scaling down exposure during BEAR and SIDEWAYS regimes.
- Establish secure, non-blocking database write paths using SQLite WAL mode to append records to the `daily_lttd` table.
- Implement strict state transition logging that explicitly captures any HMM regime shifts alongside their timestamp, posterior probability, and triggering metrics.

**Non-Goals:**
- **Live order execution:** This layer generates target position sizes but will not directly integrate with exchange APIs (e.g., Binance/Coinbase) for order routing.
- **Backtesting engine:** The Walk-Forward Optimization (WFO) and backtest runner are handled externally, though they will utilize the rules formulated here.
- **Model tweaking:** Modifications to the underlying HMM or Logistic Regression ensemble weights are out of scope.

## Decisions

1. **Regime-Weighted Position Sizing Function**
   - *Rationale:* Linear mapping of the `Final Score` to target exposure fails to account for Bitcoin's heteroskedasticity and shifting OU Half-Life. We will implement a piecewise or posterior-weighted scaling function based on the HMM Regime:
     - **BULL Regime:** Maximize capital deployment. Exposure scales directly with the `Final Score` magnitude (up to 1.0).
     - **SIDEWAYS Regime:** Dampen exposure to avoid chop and volatility clustering. Maximum exposure is capped (e.g., 0.5) to protect capital while maintaining participation.
     - **BEAR Regime:** Strict capital preservation. Target exposure is clamped to 0.0 or a minimal structural tracking allocation.
   - *Alternatives Considered:* Using the Kelly Criterion for dynamic sizing. Rejected because the non-stationarity of crypto returns and lookahead-sensitive volatility predictions make Kelly sizing brittle in this architecture.

2. **Persistence Data Model (SQLite WAL)**
   - *Rationale:* To adhere to the architecture utilized in the `quant-btc-valuation-system`, persistence will rely on SQLite configured with WAL (Write-Ahead Logging) mode. This allows concurrent reads by the Layer 6 Hono/Bun API while the Layer 5 Python engine executes its daily write. The target schema for the `daily_lttd` table will include `date`, `final_score`, `regime`, `target_exposure`, and `posterior_prob`.
   - *Alternatives Considered:* PostgreSQL or Redis. Rejected because they violate the system's lightweight, decoupled design pattern, introducing unnecessary operational complexity.

3. **Transition Logging Mechanism**
   - *Rationale:* To satisfy the hard constraint of logging every Regime transition, a dedicated `RegimeTransitionLogger` will be introduced. It will track `previous_regime` and `current_regime`. Upon a shift, it will emit a structured payload (and potentially insert into a `regime_transitions` SQLite table) containing: `timestamp`, `from_regime`, `to_regime`, `posterior_probability` of the new state, and the primary contributing metrics.
   - *Alternatives Considered:* Standard unstructured console logging. Rejected because quantitative systems require auditable, structured telemetry to evaluate the health of the HMM's state transitions.

## Risks / Trade-offs

- **[Risk] Database locking conflicts** between the Python execution script (writer) and the Hono API (reader).
  - *Mitigation:* Ensure `PRAGMA journal_mode=WAL;` is rigidly enforced during connection initialization. Use minimal transaction lifespans and configure connection timeouts properly in both Python (`timeout=10`) and Bun.
- **[Risk] Abrupt step-function shifts in exposure** when the HMM abruptly flips between regimes, which could lead to high portfolio turnover.
  - *Mitigation:* Utilize the HMM posterior probabilities to smooth the categorical transition, or apply a causal low-pass filter (Exponential Moving Average) to the target exposure output strictly enforcing past bars only (no lookahead bias).
- **[Risk] Timezone/Timestamp desync** between the BRK data feed and the execution loop.
  - *Mitigation:* Only execute target sizing using the `stamp` field provided by the BRK API response (e.g., `sth_mvrv`'s latest daily stamp) instead of relying on `datetime.now()`, ensuring strict alignment with on-chain settlement states.

## Migration Plan

1. **Scaffold the Module:** Create `src/execution/sizing.py` to house the math for target exposure generation, passing the `test_no_lookahead()` causal requirements.
2. **Setup Persistence:** Create `src/execution/database.py` with SQLite connection factory configured for WAL mode, initializing `daily_lttd` and `regime_transitions` tables if they don't exist.
3. **Transition Telemetry:** Build the logger component to track consecutive regime states and record deviations.
4. **Integration Layer:** Expose an `ExecutionEngine.run()` pipeline that accepts output from Layer 4 and seamlessly writes to Layer 5 storage.

## Open Questions

- **Shorting Capabilities:** Is the portfolio model strictly long-only (target exposure `0.0` to `1.0`), or should the system support structural short positions (`exposure < 0.0`) during high-conviction BEAR regimes? Assuming long-only for now.
- **Transition Log Storage:** Should regime transitions be recorded solely in standard stdout/file structured logs, or explicitly written to a `regime_transitions` table in SQLite so the Layer 6 React frontend can chart transition markers?
