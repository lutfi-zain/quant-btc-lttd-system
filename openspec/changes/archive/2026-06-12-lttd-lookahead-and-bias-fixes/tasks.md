## 1. Setup & Baseline

- [x] 1.1 Run the existing test suite to ensure all baseline tests are passing.
- [x] 1.2 Create a git branch `feature/LTTD-lookahead-and-bias-fixes` for these modifications.

## 2. Core Quantitative Implementations

- [x] 2.1 Refactor `infer_regime_history` in `src/regime/hmm.py` to use a causal growing-window loop.
- [x] 2.2 Correct `L1LassoEnsemble` in `src/ensemble/model.py` to specify `penalty="l1"` and `solver="liblinear"`.
- [x] 2.3 Modify the OU half-life calibration in `src/features/ou_calibration.py` to use log price levels instead of returns.
- [x] 2.4 Purge the training target boundary bar $t_{train}$ prior to fitting models in `src/ensemble/wfo.py`, `src/pipeline.py`, and `src/backtest/runner.py`.

## 3. Integration & Validation

- [x] 3.1 Verify that the updated HMM history inference, Lasso regularization, and OU calibration run correctly.
- [x] 3.2 Run the entire pytest suite using `python3 -m pytest -xvs` to ensure all tests pass.
- [x] 3.3 Validate the backtest results using the updated lookahead-free logic.
