## 1. Regime Detection (Layer 1) Modification

- [x] 1.1 Implement standard Argmax state classification in `src/regime/hmm.py`'s `infer_regime` and `infer_regime_history`.
- [x] 1.2 Implement context-bounding of inference features to a maximum of 1,095 days (trailing window) in `src/regime/hmm.py`'s `infer_regime` and `infer_regime_history`.
- [x] 1.3 Update state inference step in `src/pipeline.py` and `src/backtest/runner.py` to match new regime detection outputs.

## 2. Ensemble Aggregation (Layer 4) Modification

- [x] 2.1 Implement `PCAConsensusEnsemble` class in `src/ensemble/model.py`.
- [x] 2.2 Add PCA Consensus model option and integration into `src/pipeline.py` and `src/backtest/runner.py` to allow switching between Lasso and PCA Consensus.
- [x] 2.3 Set default ensemble aggregator to PCA Consensus in `src/pipeline.py` and `src/backtest/runner.py`.

## 3. Database Telemetry

- [x] 3.1 Ensure daily VIF values and actual PCA cumulative variance explained are calculated and persisted in telemetry.

## 4. Backend API Integration

- [x] 4.1 Update backend `backend/index.ts` to read genuine HMM state probabilities, daily VIF, and PCA variance from the database rather than simulating them.
- [x] 4.2 Validate backend Hono API response format using Bun test runner.

## 5. Verification and Validation

- [x] 5.1 Run all unit tests (`python3 -m pytest -xvs`) to verify no regressions or lookahead bias are introduced.
- [x] 5.2 Execute the full WFO backtester (`python3 -m src.backtest.runner`) and confirm the total return achieves 229%+ with a Sharpe ratio around 1.27.
- [x] 5.3 Run daily pipeline backfill script to update the sqlite database.
- [x] 5.4 Confirm that the Hono API server and Vite frontend dashboard load and display updated figures without errors.
