## Context

Bitcoin's market exhibits distinct macro regimes (BULL, BEAR, SIDEWAYS) that dictate the effectiveness of trend-following indicators. Historically, static indicator sets overfit, causing synchronized failures during regime shifts, especially as Bitcoin's Ornstein-Uhlenbeck (OU) half-life expanded to 300+ days post-2020 (the institutional era). 

The system architecture defines 6 strict layers. Layer 1 is the Regime Detection engine. This module must infer the latent market regime purely from return and volatility statistics without relying on price-based technical indicators (like moving averages or momentum) that will be used in Layer 2. This strict separation of concerns avoids multicollinearity, ensures orthogonality, and provides a robust statistical prior for dynamic position sizing.

## Goals / Non-Goals

**Goals:**
- Implement a 3-state Gaussian Hidden Markov Model (HMM) capable of dynamically classifying the macro market regime (BULL, BEAR, SIDEWAYS).
- Process daily OHLCV data to extract purely statistical features: daily log returns and realized volatility.
- Establish the `src/regime/` layer adhering to the architectural constraint: zero dependency on technical indicators or Layer 2 signals.
- Ensure the feature engineering and model inference are strictly causal (no lookahead bias).
- Output stable regime probabilities and state classifications for downstream consumption by the execution engine (Layer 5).

**Non-Goals:**
- Generating real-time directional trading signals (this is a Layer 2 concern).
- Aggregating on-chain metrics (STH-MVRV, STH-NUPL, etc.) into the HMM. The HMM acts purely on price statistics; on-chain metrics serve as external execution modifiers.
- Executing live trades or routing orders (Layer 5/6 concerns).

## Decisions

**1. Model Selection: 3-State Gaussian HMM over K-Means/GMM**
- *Rationale*: HMMs intrinsically model temporal dependence via transition matrices, which is crucial for financial markets where volatility clusters and regimes persist over time. Pure clustering models like K-Means or Gaussian Mixture Models (GMM) treat each day independently, leading to noisy "flickering" state classifications.
- *Alternatives Considered*: K-Means clustering. Rejected because it ignores the time-series nature of macro regimes.

**2. Feature Selection: Log Returns and Realized Volatility**
- *Rationale*: These two features are orthogonal to directional momentum indicators and provide a statistically sound basis for defining market phases. This maintains a Variance Inflation Factor (VIF) of zero with respect to Layer 2 technical signals.
- *Alternatives Considered*: Including Moving Averages or RSI as HMM features. Rejected because this introduces multicollinearity with Layer 2 and violates the strict layer boundaries.

**3. Volatility Calculation: Causal Rolling Window**
- *Rationale*: Realized volatility will be calculated using a strict causal rolling window (e.g., 21-day or 30-day) over log returns, ensuring data at time `t` only looks at indices `≤ t`.
- *Alternatives Considered*: Exponentially Weighted Moving Average (EWMA) or static standard deviation. EWMA may be tested during tuning, but static calculations introduce lookahead bias and are strictly prohibited.

**4. Deterministic State Label Mapping**
- *Rationale*: HMM state labels (0, 1, 2) are arbitrary post-training. We will implement deterministic post-processing to map states to human-readable regimes based on the learned distribution means:
  - Highest mean return → `BULL`
  - Lowest mean return (often negative) with highest volatility → `BEAR`
  - Near-zero mean return with lowest volatility → `SIDEWAYS`
- *Alternatives Considered*: Manual labeling. Rejected because it breaks automation and Walk-Forward Optimization (WFO).

**5. Training Paradigm: Support for Walk-Forward Optimization (WFO)**
- *Rationale*: To prevent overfitting to past epochs (especially given the changing OU half-life), the HMM must support incremental training or periodic refitting (e.g., rolling 3-year train, 6-month test).
- *Alternatives Considered*: Static fit on full history. Rejected as it guarantees overfitting to obsolete market regimes.

## Risks / Trade-offs

- **[Risk] State Flickering at Regime Boundaries** → *Mitigation*: We will utilize the posterior probabilities of the states. Transitions will only be declared if the probability of a new state exceeds a confidence threshold (e.g., > 0.70) or smoothing logic is applied downstream.
- **[Risk] HMM Non-Convergence** → *Mitigation*: Use robust initialization (e.g., initializing state means with K-Means prior to Expectation-Maximization) and bound the variance to prevent numerical instability.
- **[Risk] Lookahead Bias in Training/Standardization** → *Mitigation*: Feature standardization must be computed using expanding or rolling windows natively. Enforce strict validation using the mandatory `test_no_lookahead()` suite.

## Migration Plan

1. Create the `src/regime/` directory and `hmm.py` containing the 3-state HMM pipeline.
2. Implement strict unit tests in `tests/regime/` to enforce causal calculations and deterministic labeling.
3. Integrate the HMM output schema so it is ready to be consumed by the future Layer 4 (Ensemble Aggregation) and Layer 5 (Execution Engine).
4. No database migration is required at this stage; this establishes purely a computational module.

## Open Questions

- What is the optimal rolling window size for realized volatility (e.g., 14, 21, or 30 days) to balance responsiveness to structural breaks against day-to-day noise?
- Should the HMM be retrained daily, weekly, or monthly in a live trading environment given the expansion of the Bitcoin OU half-life? (Likely monthly/quarterly due to macro persistence).
