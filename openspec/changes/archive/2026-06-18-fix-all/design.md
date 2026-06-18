## Context

The LTTD backtest produces unacceptable metrics (Sharpe 0.43, Max Drawdown -65%). The data science audit revealed fatal statistical flaws: the dummy variable trap in HMM probabilities (causing infinite VIF), unchecked multicollinearity in on-chain metrics (MVRV and NUPL both having VIF ~50), and regime output vocabulary breaking the spec by outputting 5 states instead of 3 (`BULL`, `BEAR`, `SIDEWAYS`). We are addressing these to restore statistical soundness to the feature and regime layers.

## Goals / Non-Goals

**Goals:**
- Fix the dummy variable trap by dropping `p_sideways` before the Lasso ensemble.
- Implement strict VIF pruning in Layer 3 to drop highly collinear on-chain metrics.
- Map the HMM output states strictly to `BULL`, `BEAR`, or `SIDEWAYS`.
- Review indicator lookback windows to mitigate the lagging hit rate in Bull markets.

**Non-Goals:**
- We are not changing the core HMM implementation algorithm.
- We are not adding new technical indicators or on-chain metrics.
- We are not rewriting the execution engine logic.

## Decisions

1. **Dropping `p_sideways` for Collinearity:**
   - *Rationale:* `p_bull`, `p_bear`, and `p_sideways` sum to 1. To prevent perfectly collinear features, we must drop one dummy variable. Dropping `p_sideways` allows `p_bull` and `p_bear` to represent the directional probability axes without leakage.
   - *Alternatives considered:* L2 regularization (Ridge) could handle collinearity without dropping a column, but the architecture strictly specifies L1-Lasso for feature selection.
2. **Dynamic VIF Drop for On-Chain Metrics:**
   - *Rationale:* `sth_mvrv` and `sth_nupl` both measure STH profitability. The VIF filter should evaluate their VIFs and drop the one with the lowest Pratt measure (or highest VIF) until all features have VIF < 10.
   - *Alternatives considered:* Hardcoding the removal of `sth_nupl`. Rejected because future correlations might shift; dynamic dropping is more robust.
3. **Regime Vocabulary Mapping:**
   - *Rationale:* The execution engine expects exactly `BULL`, `BEAR`, or `SIDEWAYS` to determine sizing. Passing granular states breaks conditional logic. We will map output states in `src/regime/filter.py` or equivalent so that the pipeline strictly returns the 3 standard labels.

## Risks / Trade-offs

- **Risk:** Dropping `p_sideways` reduces explicit representation of the neutral state.
  - *Mitigation:* The model implicitly learns `p_sideways` when `p_bull` and `p_bear` are both low.
- **Risk:** Dropping `sth_nupl` removes a historically significant cycle-top leading indicator.
  - *Mitigation:* `sth_mvrv` is mathematically identical in its informational value; no edge is lost.
