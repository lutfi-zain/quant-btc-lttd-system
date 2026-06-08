## Context

The legacy Pine Script LTTD implementation utilized a simple averaging mechanism across 12 highly correlated technical indicators. This approach introduced severe multicollinearity (Variance Inflation Factor > 10 for most indicators), artificially inflating model confidence and causing synchronized failures during structural market regime shifts. 

The new system architecture introduces a strict 6-layer pipeline. This design document covers the implementation of Layer 3 (Feature Processing) and Layer 4 (Ensemble Aggregation). The objective is to consume causal, Lookahead-Bias-free indicator scores from Layer 2 (strictly ∈ {-1, +1}), eliminate their multicollinearity, and dynamically aggregate them into a statistically robust Final Score (∈ [-1.0, +1.0]) for Layer 5 (Execution Engine). This will be achieved using Principal Component Analysis (PCA) orthogonalization and an L1-Lasso Logistic Regression model, rigorously trained using Walk-Forward Optimization (WFO).

## Goals / Non-Goals

**Goals:**
- Implement PCA orthogonalization to transform raw causal indicators into uncorrelated components.
- Implement Variance Inflation Factor (VIF) diagnostics and Pratt's Measure (`dⱼ = βⱼ · rⱼ / R²`) to evaluate relative indicator importance and prune redundant features.
- Build an L1-Lasso Logistic Regression model that dynamically weights these orthogonalized features.
- Construct a Walk-Forward Optimization (WFO) pipeline with Combinatorial Purged Cross-Validation (CPCV) using rolling windows (train 3yr → validate 6mo → test 6mo).
- Produce a continuous probabilistic Final Score bounded in the range [-1.0, +1.0].

**Non-Goals:**
- Implementation of Layer 1 HMM Regime Detection or integration of on-chain Glassnode metrics.
- Construction or modification of Layer 2 causal indicators.
- Execution logic or position sizing rules (Layer 5).
- Presentation or API layer modifications (Layer 6).
- Use of symmetrical filtering or any technique that introduces lookahead bias.

## Decisions

**1. Feature Transformation Approach**
- **Decision:** Use PCA (Principal Component Analysis) orthogonalization on Layer 2 indicator scores.
- **Rationale:** Historical analysis indicates the first 3 principal components capture >85% of variance in BTC trend-following models. Orthogonal features natively resolve multicollinearity, providing a mathematically sound input matrix for the regression model.
- **Alternatives Considered:** Strict VIF-based dropping without PCA. Rejected because hard VIF thresholds (e.g., dropping all VIF > 10) might discard subtle orthogonal signals hidden within correlated indicators. PCA smoothly blends these into lower-variance components.

**2. Model Selection for Ensemble Aggregation**
- **Decision:** L1-Lasso Logistic Regression.
- **Rationale:** Logistic regression naturally outputs probabilities that seamlessly map to the required [-1.0, +1.0] Final Score range (by scaling `P(y=1)`). The L1 penalty (Lasso) acts as an inherent feature selector, shrinking the weights of noisy, less predictive PCA components to strictly zero. This provides a parsimonious model highly resistant to overfitting in crypto markets.
- **Alternatives Considered:** HMM + XGBoost. While noted in research as highly performant, tree-based ensembles are prone to overfitting on highly non-stationary financial time-series without extensive hyperparameter tuning. L1 Logistic Regression offers a more robust, interpretable baseline for initial aggregation.

**3. Cross-Validation and Training Methodology**
- **Decision:** Walk-Forward Optimization (WFO) utilizing Combinatorial Purged Cross-Validation (CPCV).
- **Rationale:** Financial time-series exhibit serial correlation. Standard K-fold CV leaks future data into the training set (Lookahead Bias). CPCV purges adjacent training bars to prevent leakage. A rolling WFO window (3yr train → 6mo validate → 6mo test) ensures the model continuously adapts to the evolving Bitcoin regime and its expanding OU Half-Life (from 40-80 days pre-2017 to 300+ days post-2020).
- **Alternatives Considered:** Expanding window without purging. Rejected because the recent past is highly correlated with the test set, creating false statistical confidence.

## Risks / Trade-offs

- **[Risk: PCA Interpretability]** → **Mitigation:** The original meaning of the variables is lost in PCA space. We will compute Pratt's Measure (`dⱼ = βⱼ · rⱼ / R²`) to map the predictive power back to the original Layer 2 indicators, ensuring the model remains explainable to stakeholders.
- **[Risk: Low variance in binary inputs]** → **Mitigation:** Layer 2 outputs are strictly `{-1, +1}`. PCA acting on these discrete vertices can occasionally produce degenerate components if standard scaling is not applied. We will enforce `StandardScaler` application before PCA to normalize variance.
- **[Risk: Computational overhead of continuous WFO]** → **Mitigation:** Because LTTD relies exclusively on daily close data, the WFO rolling steps will only be executed once daily. The computational cost of fitting L1 Logistic Regression over a 3-year daily window (~1,095 rows) is negligible.

## Migration Plan

- **Step 1:** Implement Layer 3 Feature Processing, focusing on the `StandardScaler` and PCA orthogonalization pipeline.
- **Step 2:** Implement the Layer 4 L1-Lasso Logistic Regression model with Pratt's Measure diagnostics.
- **Step 3:** Implement the WFO/CPCV engine and wire Layer 3 outputs to Layer 4 training loops.
- **Rollback Strategy:** If the WFO pipeline fails to converge in production, the system will fall back to a statistically naive equal-weighted average (bounded to [-1.0, +1.0]) and issue a critical alert.

## Open Questions

- Should the L1 regularization strength (`C` parameter) be fixed heuristically, or dynamically optimized within the 6-month validation window during each WFO roll?
- How should the model handle `NaN` values during the initial training windows before long-lookback Layer 2 indicators (e.g., 350-day MAs) have sufficiently warmed up?
