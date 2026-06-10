## 1. Setup & Legacy Cleanup

- [x] 1.1 Add `brk-client` dependency to `requirements.txt`
- [x] 1.2 Purge any legacy Pine Script-style hardcoded on-chain historical arrays (`F1_data`, etc.) from the Python codebase

## 2. On-Chain Data Ingestion (Layer 2)

- [x] 2.1 Create `OnChainFeed` module in Layer 2 for fetching `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, and `sth_supply_in_profit`
- [x] 2.2 Implement bulk historical data fetching via `brk-client` for Walk-Forward Optimization
- [x] 2.3 Implement live data fetching via `brk-client` (latest endpoint) for real-time inference
- [x] 2.4 Implement strict `stamp` causal validation in `OnChainFeed` (must be <= current bar close time)
- [x] 2.5 Implement 3-day staleness threshold handling (fallback to 0.0 on-chain weight if stale)
- [x] 2.6 Write `test_no_lookahead()` unit tests specifically for `OnChainFeed` to prevent lookahead bias

## 3. Regime Filter Implementation (Layer 1 Post-Processing)

- [x] 3.1 Implement STH-NUPL euphoric override (scales `BULL` probability to <= 0.50 when STH-NUPL > 0.75)
- [x] 3.2 Implement STH-MVRV cycle top override (limits `BULL` confidence, driving Final Score <= 0.0 when STH-MVRV > 2.0)
- [x] 3.3 Write unit tests for regime filter overrides asserting correct posterior probability modifications

## 4. Feature Processing Integration (Layer 3)

- [x] 4.1 Compute momentum features (e.g., 7-day rate of change) for on-chain metrics (`sth_sopr_24h`, etc.)
- [x] 4.2 Integrate on-chain momentum features into the Layer 3 VIF pruning pipeline
- [x] 4.3 Write tests to assert on-chain features with VIF > 10 are correctly dropped before PCA orthogonalization

## 5. Walk-Forward Optimization & Validation

- [x] 5.1 Update the WFO pipeline (Layer 4) to merge OHLCV and on-chain historical bulk data via causal `asof` merge
- [x] 5.2 Execute full backtest (2017-2025) across Walk-Forward rolling windows to validate integration
- [x] 5.3 Document the Sharpe ratio and Max Drawdown delta (before/after on-chain integration) in PR summary
