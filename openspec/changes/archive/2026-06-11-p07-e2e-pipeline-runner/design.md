## Context

The LTTD (Long-Term Trend Direction) trading system relies on a strictly layered mathematical and statistical architecture (Layers 1-5). Currently, these layers are conceptually defined but lack an automated, end-to-end orchestration mechanism. To validate statistical robustness without lookahead bias and to transition towards live execution, a unified pipeline orchestrator is needed. 

This runner will sequentially connect the layers: executing the HMM Regime Detection (Layer 1), Signal Engine (Layer 2), Feature Processing with VIF pruning and PCA (Layer 3), Ensemble Aggregation via L1-Lasso Logistic Regression (Layer 4), and finally the Execution Engine (Layer 5). Crucially, the orchestrator must implement Walk-Forward Optimization (WFO) and Combinatorial Purged Cross-Validation (CPCV) to address the non-stationary nature of Bitcoin's evolving OU half-life (e.g., the expansion to 300+ days post-2020).

## Goals / Non-Goals

**Goals:**
- Implement a unified orchestrator (`src.backtest.runner`) connecting Layer 1 through 5 chronologically.
- Develop the Walk-Forward Optimization (WFO) engine, managing rolling train (3yr), validate (6mo), and test (6mo) windows using CPCV.
- Safely fetch historical and real-time on-chain data using `brk-client` (bitview.space API), explicitly validating the `stamp` field to prevent lookahead bias.
- Dynamically execute VIF pruning (threshold < 10) and PCA orthogonalization during feature processing.
- Persist regime-weighted final scores into the SQLite WAL database (`database/lttd.db`) as `daily_lttd` records.

**Non-Goals:**
- Designing or implementing new technical indicators or on-chain metrics (the runner simply orchestrates existing or explicitly defined layer components).
- Frontend or API presentation layer updates (Layer 6 is strictly handled by the Hono/React stack).
- Direct connections to live exchange execution APIs (focus is generating the analytical `daily_lttd` state payload).

## Decisions

1. **Pipeline Architecture & Orchestration Pattern**
   - **Decision:** Implement a centralized pipeline class (`LTTDPipeline`) that sequentially calls each layer, passing strictly validated immutable DataFrames between them.
   - **Rationale:** Enforces strict layer boundaries (Regime → Signal → Feature → Ensemble → Execution) and completely prevents circular dependencies.
   - **Alternatives Considered:** A decentralized event-driven pub-sub approach was rejected because quantitative analysis—especially WFO, PCA, and Lasso—requires synchronized, full-matrix data alignment.

2. **Walk-Forward Optimization (WFO) & CPCV**
   - **Decision:** Build a rolling window generator in `src.backtest.wfo` that yields train (3yr), validate (6mo), and test (6mo) slices. Implement Combinatorial Purged Cross-Validation (CPCV) by dropping adjacent boundary bars between slices.
   - **Rationale:** Static fitting overfits to historical regimes. Bitcoin's market structure is highly non-stationary. WFO ensures the model adapts dynamically, while CPCV prevents data leakage through serial correlation.
   - **Alternatives Considered:** Traditional K-Fold Cross-Validation was rejected due to data leakage in time-series data.

3. **On-Chain Data Ingestion & Causality**
   - **Decision:** Use the BRK API bulk endpoint via `brk-client` to fetch `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, and `sth_supply_in_profit`. Join using pandas `merge_asof` matching on the BRK `stamp` field explicitly against the previous daily close to guarantee $t-1$ visibility at time $t$.
   - **Rationale:** Replacing historical static Pine Script arrays with real API data is mandatory. Validating the `stamp` field strictly enforces causality.
   - **Alternatives Considered:** Simple timestamp alignment was rejected because event occurrence timestamp differs from data confirmation timestamp; the `stamp` field acts as the explicit `data_as_of` mechanism.

4. **Dynamic Multicollinearity Pruning (VIF + PCA)**
   - **Decision:** During Layer 3 (Feature Processing), compute VIF iteratively across all active indicator columns. If the maximum VIF > 10, drop that feature and repeat. Apply PCA orthogonalization to the surviving features.
   - **Rationale:** Mitigates the synchronized failure risk identified during the legacy audit of 12 correlated technical indicators. Multicollinearity distorts regression weights.
   - **Alternatives Considered:** Manual static feature dropping was rejected because indicator correlations shift dynamically across WFO rolling windows.

5. **Persistence Mechanism**
   - **Decision:** The Execution Engine (Layer 5) utilizes `sqlite3` and pandas `to_sql` (append mode) with a unique index constraint on the date column to insert/upsert into the `daily_lttd` table within `database/lttd.db` (configured for WAL mode).
   - **Rationale:** Aligns with the standard project database architecture, efficiently bridging the Python compute pipeline to the Hono backend read layer.

## Risks / Trade-offs

- **Risk:** Performance bottlenecks during the rolling WFO loop. Repeatedly fitting the 3-state HMM, calculating VIF iteratively, and running PCA/Lasso every 6 months across multiple years could be slow in Python.
  - **Mitigation:** Vectorize operations using numpy/scipy where possible. If runtime becomes prohibitive, parallelize independent WFO window processing using `joblib` or `multiprocessing`.

- **Risk:** BRK API latency or missing data breaks the pipeline matrix.
  - **Mitigation:** Implement robust error handling and exponential backoff. If data is excessively stale (e.g., `stamp` is older than expected by > 48h), raise a strict `StaleDataError` to halt execution rather than hallucinating signals or trading on stale indicators.

- **Risk:** CPCV implementation errors leaking future data.
  - **Mitigation:** Enforce strict unit testing (`test_no_lookahead`) on the WFO engine using dummy monotonic arrays to mathematically prove no index overlap exists between the purged train, validate, and test slices.

## Migration Plan

1. Scaffold the `src.backtest.runner` CLI and argument parser.
2. Implement the `BRKIngestionService` to reliably pull on-chain metrics via `brk-client` and align the `stamp`.
3. Construct the `WFOEngine` implementing the 3yr/6mo/6mo sliding window and the CPCV purging gaps.
4. Integrate the pipeline sequence: pass historical BTC price + BRK data through Regime (HMM) → Signal (Causal Filters) → Feature (VIF/PCA) → Ensemble (Lasso).
5. Build the SQLite DB upsert functionality for the final `daily_lttd` execution outputs.
6. Run comprehensive verification against `pytest --cov`, ensuring >85% coverage and confirming zero lookahead bias across rolling windows.

## Open Questions

- What is the precise purging duration (in days) required for the CPCV gap between train and test sets to eliminate serial correlation effectively? (Defaulting to 5 days, pending quantitative verification).
- Should the orchestrator handle automatic retries or fallback parameters for the HMM layer if it fails to converge within the maximum iterations on a particularly volatile data slice during WFO?
- Will the final daily live execution job be triggered via a cron job on the host system, or managed through an external scheduler?
