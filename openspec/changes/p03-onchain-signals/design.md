## Context

Bitcoin's structural mean-reversion behavior and cycle shifts are fundamentally tied to on-chain holder dynamics, particularly the Short-Term Holder (STH) cohort. In the current state of the LTTD system, the Hidden Markov Model (HMM) relies exclusively on OHLCV-derived features (returns and realized volatility). While effective, pure price momentum metrics suffer from delayed transitions and multicollinearity (VIF > 10) during distribution and capitulation phases. 

Historically, on-chain metrics like STH-MVRV and STH-NUPL lead price tops by 3–14 days. The legacy Pine Script attempted to model this using hardcoded historical data arrays, which completely breaks real-time inference and introduces severe lookahead bias. 

This design document outlines the architecture for integrating live, causality-preserved on-chain metrics via the `brk-client` into the LTTD pipeline as orthogonal regime filters.

## Goals / Non-Goals

**Goals:**
* Integrate dynamic data ingestion for STH-MVRV, STH-NUPL, STH-SOPR, and STH-Supply in Profit via `brk-client` from `https://bitview.space`.
* Implement a causal validation mechanism that guarantees no lookahead bias by strictly asserting the `stamp` fields of on-chain responses.
* Apply overriding regime filters (e.g., scaling down maximum exposure when STH-NUPL > 0.75) to the HMM posterior probabilities in Layer 1.
* Expose normalized on-chain metrics as Layer 2 signals that feed into Layer 3 (Feature Processing) while maintaining the rigorous VIF < 10 threshold.

**Non-Goals:**
* Completely replacing the OHLCV-based HMM with an on-chain-only model.
* Integrating Long-Term Holder (LTH) metrics, which are slower to react and better suited for macro-cycle forecasting than 120-350 day LTTD trend direction.
* Re-training the underlying HMM emission matrices.

## Decisions

1. **Data Fetching & Caching Strategy**
   * **Decision:** Use `brk-client` to fetch on-chain data. For historical backtesting and Walk-Forward Optimization (WFO), use the bulk endpoint (`GET /api/series/bulk`). For live inference, use the latest endpoint (`GET /api/series/{name}/day/latest`). 
   * **Rationale:** The bulk endpoint is optimized for retrieving long time-series data efficiently without rate limit concerns. Live execution requires the absolute latest confirmed value.
   * **Alternative Considered:** Calling raw REST endpoints directly. Rejected because `brk-client` provides typed models and native integration within the Python ecosystem.

2. **Causal Alignment and Lookahead Prevention**
   * **Decision:** Implement an `OnChainFeed` interface in Layer 2 that performs a strict `stamp` validation: `assert brk_feed.stamp >= current_date - timedelta(days=1)`. During merging, on-chain data is joined using an `asof` merge, matching the latest `stamp` that is strictly less than or equal to the OHLCV bar's close time.
   * **Rationale:** Blockchain data settlement requires confirmations. A daily metric for day `T` is often only finalized early on `T+1`. Forward-filling the last confirmed `stamp` is the only mathematically sound way to avoid referencing future data points in backtesting.
   * **Alternative Considered:** Interpolation of missing days. Rejected because it relies on future boundaries, introducing lookahead bias.

3. **Regime Filter Architecture**
   * **Decision:** Apply on-chain metrics as a post-processing heuristic (overriding constraint) to the Layer 1 Regime output, rather than incorporating them as features directly into the HMM observation matrix.
   * **Rationale:** The 3-state HMM is well-calibrated for continuous daily log returns and volatility. Injecting bounded on-chain ratios (which can spike exponentially) destabilizes the HMM's Gaussian emission assumptions. Using them as deterministic constraints (e.g., overriding the `BULL` state probability when STH-MVRV > 2.0) preserves HMM stability while capturing the cycle tops.

4. **Layer 3 Feature Integration**
   * **Decision:** On-chain metric rates of change (e.g., 7-day momentum of STH-SOPR) will be fed into Layer 3 as candidate features.
   * **Rationale:** While on-chain data is fundamentally derived from UTXO state (orthogonal to price data), extreme market moves can cause transient correlation. They must still pass the rigorous Variance Inflation Factor (VIF < 10) pruning before reaching the Layer 4 Ensemble.

## Risks / Trade-offs

* **[Risk] Upstream API Failure:** The `bitview.space` API could experience downtime, preventing live execution from fetching the latest `stamp`.
  * **Mitigation:** The `OnChainFeed` interface must gracefully degrade by forward-filling the last known valid metric up to a maximum staleness threshold (e.g., 3 days). If data is excessively stale, the system will apply a 0.0 (neutral) signal weight for the on-chain component and fall back entirely to technical OHLCV features.
* **[Risk] Timestamp Misalignment:** Differences between the UTC close of crypto exchanges (OHLCV data) and the UTC calculation window of on-chain data.
  * **Mitigation:** Ensure all data is timezone-aware. All joins must be strictly causal right-joins on the OHLCV timeline.

## Migration Plan

1. **Purge Legacy Code:** Delete all Pine Script-style hardcoded on-chain historical arrays (`F1_data`, etc.) from the codebase.
2. **Implement Data Layer:** Add `brk-client` to `requirements.txt`. Build the `OnChainFeed` ingestion module.
3. **Unit Testing:** Write `test_no_lookahead()` cases specifically for the `OnChainFeed` to guarantee causal boundaries.
4. **Integration:** Update Layer 1 to accept the on-chain filters and Layer 3 to process on-chain features in the WFO pipeline.
5. **Backtest Validation:** Run a full Walk-Forward Optimization across the 2017-2025 dataset to verify the expected reduction in Max Drawdown.

## Open Questions

* What should be the precise numerical threshold for the STH-SOPR euphoric override? Currently proposed: STH-MVRV > 2.0 and STH-NUPL > 0.75 based on research, but SOPR needs defining.
* Should the STH-Supply in Profit metric be used as an absolute ratio (e.g., > 95% is euphoric) or as a rolling Z-score over the 800-1,200 day context window?
