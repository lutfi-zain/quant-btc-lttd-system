# Delta Specifications: Lookahead and Bias Fixes

## ADDED Requirements

### Requirement: Causal HMM Regime Inference
Enforce that HMM regime probability estimation does not access future observations. The inference algorithm must be strictly causal.

#### Scenario: Day-by-Day Historical Regime Prediction
- **GIVEN** a trained HMM model, close price series up to time $t$, and state-to-regime mappings.
- **WHEN** inferring the market regime at bar $t$.
- **THEN** the model SHALL only read closing prices from indices $\le t$.
- **AND** the computed posterior probabilities for BULL, BEAR, and SIDEWAYS SHALL sum to 1.0.
- **AND** the Viterbi alignment or posterior smoothing SHALL NOT utilize any pricing data from indices $> t$.

---

### Requirement: Boundary Target Variable Purging
Enforce that the training targets ($y$) do not leak tomorrow's price direction at the boundaries of the training folds.

#### Scenario: WFO Fold boundary label verification
- **GIVEN** a walk-forward optimization split with a training fold index ending at $t_{train}$ and test fold starting at $t_{test}$.
- **WHEN** constructing the target variable $y_t = \text{sign}(\text{close}_{t+1} - \text{close}_t)$.
- **THEN** the target value at $t_{train}$ SHALL NOT leak the close price of $t_{test}$.
- **AND** the training set target vector $y_{\text{train}}$ SHALL drop or purge the last observation at $t_{train}$ to prevent lookahead bias.

---

### Requirement: L1 Lasso Feature Selection
Enforce that the ensemble model runs an L1 Lasso regularized Logistic Regression.

#### Scenario: Sparse Ensemble Coefficients
- **GIVEN** a standardized feature matrix and a binary target vector.
- **WHEN** fitting the `L1LassoEnsemble` model.
- **THEN** the underlying model SHALL use L1 regularization (Lasso).
- **AND** the coefficients of non-informative or collinear features SHALL be driven to exactly 0.0.

---

### Requirement: Log-Price OU Half-Life Calibration
Enforce that the Ornstein-Uhlenbeck (OU) mean-reversion speed estimation models price levels instead of returns.

#### Scenario: OU Half-Life Parameter Estimation
- **GIVEN** a historical price series.
- **WHEN** calibrating the AR(1) model for OU half-life.
- **THEN** the input series to the regression SHALL be log price levels ($\ln(\text{close})$) instead of log returns.

---

## Non-Goals
- Modifying the number of HMM states (fixed at 3 states: BULL, BEAR, SIDEWAYS).
- Adding new technical indicators or changing the VIF pruning threshold (fixed at 10.0).
- Rewriting the frontend presentation layer charts or visualization components.
