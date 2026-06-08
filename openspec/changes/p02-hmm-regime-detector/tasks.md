## 1. Project Setup and Infrastructure

- [x] 1.1 Create `src/regime/` directory structure and `__init__.py`
- [x] 1.2 Create `tests/regime/` directory for unit tests
- [x] 1.3 Initialize `requirements.txt` with essential dependencies (`pandas`, `numpy`, `hmmlearn`, `scikit-learn`, `pytest`, `pytest-cov`)

## 2. Feature Preparation Pipeline

- [x] 2.1 Implement strictly causal `calculate_log_returns` function (`ln(P_t / P_{t-1})`) in `src/regime/features.py`
- [x] 2.2 Implement strictly causal `calculate_realized_volatility` using a 21-day rolling window
- [x] 2.3 Create `prepare_features` to orchestrate log returns and volatility into the exact 2D array expected by HMM
- [x] 2.4 Write `test_features.py` containing `test_no_lookahead()` to guarantee zero leakage from future bars

## 3. HMM Model Training Pipeline

- [x] 3.1 Implement robust K-Means initialization logic for the 3-state HMM in `src/regime/hmm.py` to ensure convergence
- [x] 3.2 Implement `train_hmm` using `hmmlearn.GaussianHMM(n_components=3)`
- [x] 3.3 Add validation to raise `ValueError` (or custom exception) if less than 120 days of data is provided
- [x] 3.4 Implement deterministic state labeling (highest return = BULL, lowest return/highest vol = BEAR, zero return/lowest vol = SIDEWAYS)
- [x] 3.5 Write `test_hmm_training.py` to verify state labeling, non-convergence prevention, and < 120 days exception

## 4. HMM Inference Pipeline

- [x] 4.1 Implement `infer_regime` to output posterior probabilities `[P(Bull), P(Bear), P(Sideways)]` that sum to 1.0
- [x] 4.2 Implement threshold logic in inference: classify as BULL only if `P(Bull) > 0.70`
- [x] 4.3 Write `test_hmm_inference.py` to strictly verify posterior probability sums and test daily causal inference

## 5. Architectural Boundaries and Verification

- [x] 5.1 Implement a clean public API (`src/regime/__init__.py` or facade) to expose only necessary training and inference functions
- [x] 5.2 Write `test_architecture.py` to assert that `src/regime/` does not import from `src/signals/` or `src/features/`
- [x] 5.3 Run `python -m pytest -xvs` and `python -m pytest --cov` to confirm all tests pass and coverage is adequate
