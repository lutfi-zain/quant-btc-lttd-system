## Context

<!-- Background and current state -->
This design document addresses the critical lookahead biases, regularizer mismatches, and mathematical calibration issues identified in the LTTD system:
1. **HMM Lookahead Bias:** The `infer_regime_history` method runs a global forward-backward smoothing path which leaks future prices into past regime predictions.
2. **Target Label Leakage:** The target variable `y` is calculated over the entire dataset with `shift(-1)` prior to fold splitting, leading to lookahead bias at the boundaries of the training set.
3. **Regularizer Mismatch:** `L1LassoEnsemble` is defaulting to L2 regularization because `penalty="l1"` was omitted in scikit-learn's `LogisticRegression`.
4. **OU Calibration Input:** Ornstein-Uhlenbeck parameter estimation is incorrectly run on log returns instead of log price levels.

## Goals / Non-Goals

**Goals:**
- Eliminate all lookahead biases in regime inference and WFO folds.
- Align the regularizer in the ensemble model with the spec's target (L1 Lasso).
- Correct the OU half-life parameter estimation methodology.
- Ensure all tests pass.

**Non-Goals:**
- Introducing new data feeds or indicators.
- Changing database schemas or API definitions.

## Decisions

### Decision 1: Causal HMM Inference in `infer_regime_history`
- **Choice:** Convert `infer_regime_history` to run an expanding-window loop that performs inference causally up to day $t$ (equivalent to progressive live inference).
- **Rationale:** Computing the state probabilities at time $t$ using only data up to $t$ removes lookahead bias and matches the online execution environment.
- **Alternatives Considered:** Implementing a custom forward pass (Alpha pass). Although more computationally efficient, it is highly prone to bugs and difficult to maintain compared to using the library's `predict_proba()` on growing slices.

### Decision 2: Boundary Target Variable Purging & Embargoing
- **Choice:** Adjust target variable generation to avoid lookahead at training fold boundaries. When splitting training and testing folds, drop the last training index $t_{train}$ where `shift(-1)` references $t_{test}$.
- **Rationale:** Purging the boundary row ensures that no test data leaks into the training fit.

### Decision 3: Explicit L1 Lasso Regularization
- **Choice:** Configure `LogisticRegression(penalty="l1", solver="liblinear", random_state=42)` in `L1LassoEnsemble`.
- **Rationale:** Specifying `penalty="l1"` is mandatory to override the default L2 (Ridge) penalty. `liblinear` is a robust solver for L1 regularization on small datasets.

### Decision 4: Log-Price Levels for OU Calibration
- **Choice:** Update `estimate_ou_halflife` to perform regression on log price levels ($\ln(\text{price})$) instead of log returns.
- **Rationale:** The Ornstein-Uhlenbeck process models mean-reverting price levels. Autocorrelation of returns measures price momentum, not mean-reversion.

## Risks / Trade-offs

- **[Risk]** Running HMM in an expanding loop increases backtest execution time.
  - **Mitigation:** Only run the expanding-window loop over the test interval. Since the test window is short (6 months), the performance impact is negligible.
