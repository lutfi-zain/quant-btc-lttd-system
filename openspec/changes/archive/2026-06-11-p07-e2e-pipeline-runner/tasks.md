## 1. BRK Ingestion & Data Synchronization

- [x] 1.1 Implement `BRKIngestionService` with a typed `BRKFeed` interface using `brk-client` to bulk fetch `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, and `sth_supply_in_profit`.
- [x] 1.2 Implement the 1,200-day minimum historical lookback initialization logic for optimal uptrend detection context.
- [x] 1.3 Add strict validation on the `stamp` field (`brk_feed.stamp >= current_date - timedelta(days=1)`) to enforce real-time causality and prevent Lookahead Bias.
- [x] 1.4 Implement `DataStaleException` behavior to halt pipeline execution if the `stamp` validation fails (preventing trading on stale metrics).

## 2. Walk-Forward Optimization (WFO) Engine

- [x] 2.1 Construct `WFOEngine` to slice the historical data into rolling windows of 3-year train, 6-month validate, and 6-month test splits.
- [x] 2.2 Implement Combinatorial Purged Cross-Validation (CPCV) logic to purge overlapping embargo bars (up to 350 days based on OU Half-Life) between train/val/test splits.
- [x] 2.3 Write `test_no_lookahead` unit tests using monotonic dummy arrays to mathematically prove zero index overlap and prevent serial correlation leakage.

## 3. Pipeline Architecture & Orchestration

- [x] 3.1 Scaffold the `src.backtest.runner` CLI and the central `LTTDPipeline` orchestrator class.
- [x] 3.2 Integrate Layer 1 (Regime Detection HMM) and Layer 2 (Causal-Only Signal Engine) into the chronological pipeline sequence using immutable DataFrames.
- [x] 3.3 Implement iterative VIF pruning in Layer 3 (Feature Processing) to ensure exactly 0 features with VIF > 10 remain, followed by PCA orthogonalization.
- [x] 3.4 Integrate Layer 4 (Ensemble Aggregation via L1-Lasso Logistic Regression) utilizing the WFO Engine to produce Final Scores ∈ [-1.0, +1.0].
- [x] 3.5 Connect Layer 5 (Execution Engine) to output regime-weighted position sizing and write exactly one `daily_lttd` row to `database/lttd.db` (WAL mode) via `sqlite3` and `to_sql`.

## 4. Verification & E2E Testing

- [x] 4.1 Write integration tests verifying the full causal continuity across the pipeline (enforcing no `t+k` array access for `k > 0`).
- [x] 4.2 Aggregate test set performance across all rolling windows to compute true out-of-sample metrics (Sharpe ratio target 1.8-2.2, max drawdown strictly < 25.0%).
- [x] 4.3 Run `python -m pytest --cov` to confirm all orchestrated components and WFO logic meet the >85% test coverage requirement.
