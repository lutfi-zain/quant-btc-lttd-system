## Why

The LTTD (Long-Term Trend Direction) system is architected across distinct mathematical and statistical layers, from Regime Detection (HMM) to Ensemble Aggregation (L1-Lasso Logistic Regression). To validate the statistical robustness of our causal indicators and regime filters without lookahead bias, we must orchestrate these separated layers into a unified, automated end-to-end pipeline. The primary statistical motivation is to enable Walk-Forward Optimization (WFO) combined with Combinatorial Purged Cross-Validation (CPCV) over historical data. This ensures our out-of-sample predictability is valid, appropriately capturing the non-stationary nature of Bitcoin's OU half-life. This unified runner solves the problem of disjointed layer execution and prepares the system for quantitative evaluation and live deployment.

## What Changes

- Implement the unified pipeline orchestrator (`src.backtest.runner` and daily execution runner) connecting Layers 1 through 5 chronologically.
- Integrate the Walk-Forward Optimization (WFO) loop, managing rolling train (3yr), validate (6mo), and test (6mo) windows into the pipeline execution.
- Fetch on-chain data (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`) systematically via the `brk-client` bulk endpoint during pipeline execution, validating the `stamp` field to strictly prevent lookahead bias.
- Connect Layer 4 (Ensemble Aggregation) outputs directly to Layer 5 (Execution Engine) to persist the resulting `daily_lttd` regime-weighted scores into the SQLite WAL database (`database/lttd.db`).
- Execute PCA orthogonalization and VIF pruning (threshold < 10) dynamically during the feature processing phase of the run.

### Backtest Impact
This runner establishes the exact apparatus required to accurately measure backtest impact via CPCV. By strictly enforcing causal-only filtering across the pipeline and dropping lookahead-biased signals (e.g., SGF), we anticipate the true out-of-sample Sharpe ratio to stabilize realistically between 1.8 and 2.2. The dynamic regime-weighted sizing executed by this pipeline aims to constrain maximum drawdown strictly below 25% by decisively de-allocating during HMM-inferred BEAR regimes.

### Data Dependencies
This change formalizes the real-time data dependency on the `brk-client` and the `https://bitview.space/api/series/bulk` endpoint. Historical static arrays are completely bypassed in favor of API-based ingestion. **No new technical indicators are introduced** in this change; therefore, the runner utilizes the existing Feature Processing layer mechanisms to correctly enforce VIF redundancy (<10) across existing indicators.

## Capabilities

### New Capabilities
- `pipeline-orchestrator`: End-to-end orchestration logic safely passing data from Layer 1 (Regime Detection) through Layer 5 (Execution Engine) without future data leakage.
- `wfo-engine`: The engine controlling Walk-Forward Optimization, responsible for slicing data into purged train/validate/test sets for CPCV.
- `brk-ingestion-sync`: The systematic fetching and synchronization of bitview.space API data using `brk-client`, safely mapping `stamp` records to execution states.

### Modified Capabilities

## Impact

- **Affected Layers:** Orchestrates all backend mathematical layers: Regime (1), Signal (2), Feature (3), Ensemble (4), and Execution (5).
- **Code/APIs:** Introduces the `src.backtest.runner` module to act as the primary CLI and pipeline entrypoint.
- **Dependencies:** Strictly binds `brk-client` into the execution path for live and historical execution.
- **Systems:** Bridges the Python computational pipeline with the persistent SQLite database (`database/lttd.db`), providing the finalized data payload that Layer 6 (Presentation) will consume via the Hono v4 backend.
