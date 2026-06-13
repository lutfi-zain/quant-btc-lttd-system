## Context

The current LTTD (Long-Term Trend Direction) system uses unbounded indicators and discrete {-1, 1} signals. To reliably match the historical ground truth (defined in `isp-regimes-btcusd.csv` and `isp-signals-btcusd.csv`), we need a mathematical guarantee of coherence across all components. The transition to a bounded [0,1] probability/intensity space enables an Additive Average Consensus model. By applying Machine Learning, we can discover the optimal constituent weights to reproduce the target regimes while strictly enforcing out-of-sample robustness through causal filters and L1 regularization.

## Goals / Non-Goals

**Goals:**
- Scale all Layer 2 indicator outputs to a bounded [0,1] continuous space without lookahead bias.
- Formulate the ensemble aggregation (Layer 4) as a supervised ML problem predicting the regime target.
- Forward-fill the sparse regime target CSV to create a daily ground-truth vector ($y_t$).
- Enforce L1 regularization and monotonic constraints on the ML model to prevent memorizing the past.
- Recreate the 5-state regime classification (Strong Bull, Weak Bull, Neutral, Weak Bear, Strong Bear) via tuned thresholding of the final score.

**Non-Goals:**
- Creating new on-chain or technical indicators from scratch (we will use the existing suite).
- Building the actual live execution/trading adapter (Layer 5) in this change.
- Altering the backend API or frontend visualization layers (Layer 6).

## Decisions

**Decision 1: Rolling Empirical MinMax/CDF for Normalization**
- **Rationale:** Standard normalization across the entire dataset introduces lookahead bias. We will use a rolling 800-1200 day lookback window to calculate the minimum and maximum bounds dynamically. This guarantees causality.

**Decision 2: Target Forward-Filling**
- **Rationale:** The target `isp-regimes-btcusd.csv` contains sparse regime transition dates. To train an ML model, we must forward-fill these states to assign a continuous daily target class (e.g., Strong Bull = 1.0, Strong Bear = 0.0) so the model can optimize against daily $X_t$ vectors.

**Decision 3: L1-Regularized Logistic/Linear Consensus**
- **Rationale:** A simple average assumes all indicators are equally predictive. By using an L1-regularized model (Lasso), the system will automatically perform feature selection, zeroing out the weights of highly collinear (redundant) indicators. This ensures that only the most robust, independent signals drive the final average. Monotonic constraints will be applied so that the model doesn't learn inverse relationships just to fit noise.

**Decision 4: Threshold-Based Regime Mapping**
- **Rationale:** The ML model will output a continuous score from 0.0 to 1.0. We will map this back to the 5 distinct regimes using fixed intervals (e.g., [0.8 - 1.0] -> Strong Bull, [0.6 - 0.79] -> Weak Bull, etc.).

## Risks / Trade-offs

- **Risk:** Overfitting to the target CSV.
  - **Mitigation:** We are enforcing L1 regularization, monotonic constraints, and will rely on walk-forward validation (WFO) to ensure the weights generalize.
- **Risk:** Lag during regime transitions due to rolling windows.
  - **Mitigation:** While an 800-day window is slow, the L1 model will likely select a mix of fast technical indicators (like RSI) and slow on-chain indicators (like NUPL) to balance responsiveness and stability.
