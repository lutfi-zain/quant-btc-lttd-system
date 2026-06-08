## Context

Bitcoin's macroeconomic behavior is not stationary. Historically, its Ornstein-Uhlenbeck (OU) mean-reversion half-life has shifted from a 40–80 day cycle prior to 2017 to over 300 days in the post-2020 institutional era. The LTTD (Long-Term Trend Direction) system currently relies on static lookback windows for its causal Technical Indicators. This fixed lookback mechanism leads to significant phase lag during regimes characterized by rapid mean reversion, while suffering from premature signal decay during persistent trends. To align the LTTD system's contextual windows mathematically with the current epoch, we need to introduce an OU Half-Life estimator. This estimator will continuously calibrate the structural mean-reversion speed from daily log returns, explicitly adapting the `CausalFilter` context bounds strictly within the empirically bounded range of 120–350 days.

## Goals / Non-Goals

**Goals:**
- Formulate a statistical Ornstein-Uhlenbeck calibration pipeline within Layer 3 (`src/features/`) that dynamically estimates the mean-reversion half-life of BTC.
- Update Layer 2 (`src/signals/`) `CausalFilter` to accept dynamically resizing windows based on the OU Half-Life.
- Restrict window size fluctuations to the bounds of [120, 350] days to prevent pathological indicator configurations.
- Eliminate Lookahead Bias strictly by applying WFO (Walk-Forward Optimization) to OU parameter estimation (quarterly recalibration).

**Non-Goals:**
- Integrating the OU Half-Life directly as an additive feature in the ensemble (it is a structural meta-parameter, not a directional signal).
- Changing Layer 1 (HMM Regime Detection) logic or adding new regimes.
- Using the estimator for intra-day or short-term trading signals (strictly LTTD scope).
- Adding new external on-chain dependencies; the estimator uses solely OHLCV-derived daily log returns.

## Decisions

**1. Estimation Method: OLS Calibration of the OU Process vs. Maximum Likelihood Estimation (MLE)**
- **Decision:** Use OLS (Ordinary Least Squares) regression on the discrete-time AR(1) representation of the OU process.
- **Rationale:** The OU process $dx_t = \theta (\mu - x_t)dt + \sigma dW_t$ can be discretized to an exact AR(1) process $x_{t+1} = a + b x_t + \epsilon$. Running an OLS regression ($x_{t+1}$ against $x_t$) is computationally light, deterministic, and highly stable compared to MLE numerical optimizers that can fail to converge on noisy cryptocurrency returns. The half-life is strictly extracted as $HL = -\frac{\ln(2)}{\ln(|b|)}$.
- **Alternatives Considered:** Maximum Likelihood Estimation (MLE) using `scipy.optimize`. Rejected because MLE runs the risk of non-convergence, particularly when realized volatility spikes unpredictably, leading to undefined lookbacks in real-time execution.

**2. Calibration Frequency: Quarterly WFO Recalibration vs. Daily Rolling Window**
- **Decision:** Recalibrate the OU Half-Life on a quarterly basis using Walk-Forward Optimization (WFO).
- **Rationale:** The OU Half-Life measures macroeconomic regime epochs, which shift slowly. Updating the window size every single day introduces jitter into the Causal Filters, leading to unstable `Indicator Score` crossovers. Quarterly calibration (e.g., using a 3-year rolling context window to estimate the parameter) ensures stability and aligns perfectly with the CPCV pipeline.
- **Alternatives Considered:** Daily rolling calibration. Rejected as it produces noisy window sizes, causing indicators to flip signals based on filter bound shifting rather than underlying price action.

**3. Window Translation Logic: Direct Mapping vs. Piecewise Function**
- **Decision:** Apply a direct linear clamping function `Window(t) = max(120, min(350, HL(t)))`.
- **Rationale:** Research indicates the valid structural epoch for BTC sits between 120 and 350 days. Clamping the raw half-life estimation cleanly forces indicators to respect this boundary. 
- **Alternatives Considered:** A step-function mapping (e.g., `< 200 -> 120`, `> 200 -> 350`). Rejected because it creates discontinuity spikes in indicator values at the regime boundary.

## Risks / Trade-offs

- **[Risk: Divergent AR(1) Process (b >= 1)]** → **Mitigation:** In explosive trending markets, the AR(1) coefficient $b$ can reach or exceed 1, making the half-life mathematically undefined (infinite). We will mitigate this by catching $b \ge 1$ and defaulting to the upper bound (350 days), signifying a purely trending (non-mean-reverting) regime.
- **[Risk: CausalFilter Memory Leak / Indexing Error]** → **Mitigation:** Dynamically resizing array bounds in `scipy.signal` can lead to shape mismatches in pandas/numpy. Mitigation is to recreate filter coefficients `(b, a)` only when the epoch boundary recalibrates quarterly, rather than sliding dynamically bar-by-bar.
- **[Risk: Backtest Invalidation]** → **Mitigation:** Hardcoded 200-day window backtests will break. We will persist the static 200-day configuration as a legacy fallback parameter in the `Runner` specifically for unit-test backward compatibility, explicitly flagged as `--legacy-fixed-window`.

## Migration Plan

1. **Phase 1: Feature Implementation**
   - Add `ou_calibration.py` to `src/features/`.
   - Write `test_no_lookahead` for the AR(1) OLS pipeline to strictly verify no future data leaks.
2. **Phase 2: Signal Layer Integration**
   - Refactor `src/signals/base.py` `CausalFilter` to accept a `dynamic_lookback` callback/parameter.
3. **Phase 3: Backtest Integration**
   - Inject the OU Half-Life computation into the existing WFO engine inside `src/ensemble/wfo.py` during the 3-year train boundary.
4. **Rollback Strategy:** Revert the base `CausalFilter` default behavior to a static 200-day integer if the OLS calibration throws structural exceptions during live runs.

## Open Questions

- Should the OU process be calibrated strictly on log price, or on the detrended residual of price against the Layer 1 HMM baseline?
- Does shifting the window size quarterly introduce a 1-bar lag in `Indicator Score` outputs on the day of the transition, and if so, do we need a 5-day smoothing transition function?
