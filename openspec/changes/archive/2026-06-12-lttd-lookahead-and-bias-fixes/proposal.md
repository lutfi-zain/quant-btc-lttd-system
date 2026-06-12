## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->
The current LTTD implementation contains critical quantitative vulnerabilities that compromise the statistical validity of the backtest:
1. **Regime Detection Lookahead:** `infer_regime_history` utilizes `predict_proba` (forward-backward algorithm), introducing lookahead bias by using future returns to estimate past regimes.
2. **Target Label Leakage:** The target label $y$ is computed globally using `shift(-1)` prior to slicing the WFO train/test folds, leakage-contaminating the training sets with tomorrow's close price.
3. **Model regularizer mismatch:** The ensemble `L1LassoEnsemble` is misconfigured to run L2 Ridge regression instead of L1 Lasso because `penalty="l1"` was omitted while using the `liblinear` solver.
4. **Incorrect OU Calibration Input:** The Ornstein-Uhlenbeck half-life estimator calibrates on daily log returns instead of log price levels, resulting in invalid mean-reversion speed estimations.

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->
1. **Causal HMM Inference:** Transition `infer_regime_history` to run a causal forward-only pass (Alpha pass) or slide the inference window progressively.
2. **CPCV Purging & Causal Targets:** Drop the boundary train rows at $t_{train}$ where `shift(-1)` references $t_{test}$. Add strict CPCV purging between train and test sets in `run_wfo_pipeline()`.
3. **L1 Lasso Ensemble Correction:** Reconfigure the ensemble model to explicitly use `penalty='l1'` with `solver='liblinear'` to restore feature sparsity.
4. **Log-Price OU Estimator:** Update `ou_calibration.py` to calculate the AR(1) mean-reversion half-life on log price levels (`np.log(close)`) instead of log returns.

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Replace <name> with kebab-case identifier (e.g., user-auth, data-export, api-rate-limiting). Each creates specs/<name>/spec.md -->

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
- `hmm-regime-classification`: Update inference to enforce causal forward-only posterior probability estimation.
- `walk-forward-optimization`: Enforce purging of boundary labels between train and test folds to prevent return leakage.
- `ensemble-aggregation`: Enforce strict L1 Lasso regularizer coefficients with feature sparsity.
- `ou-halflife-estimator`: Modify regression model inputs to operate on log price levels instead of log returns.

## Impact

<!-- Affected code, APIs, dependencies, systems -->
- **Files Modified:**
  - [hmm.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/regime/hmm.py)
  - [model.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/ensemble/model.py)
  - [wfo.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/ensemble/wfo.py)
  - [ou_calibration.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/features/ou_calibration.py)
  - [runner.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/backtest/runner.py)
  - [pipeline.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/pipeline.py)
- **APIs Affected:** None (changes are localized to Python quantitative calculations).
- **Backtest Impact:** Annualized Sharpe ratio and return values will adjust to reflect realistic, lookahead-free historical performance.
