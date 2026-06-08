## 1. Setup and Boilerplate

- [ ] 1.1 Create `src/signals/fourier_supertrend.py` and define `AdaptiveFourierSupertrend` inheriting from `CausalFilter`
- [ ] 1.2 Create `tests/signals/test_fourier_supertrend.py` test file structure
- [ ] 1.3 Update `src/signals/__init__.py` to expose the new indicator

## 2. Core Mathematical Implementation

- [ ] 2.1 Implement rolling window FFT using `scipy.fft` to extract the dominant spectral period ($T_{dom}$)
- [ ] 2.2 Add noise mitigation via a rolling 5-day median of $T_{dom}$ or low-pass EMA on raw prices before FFT
- [ ] 2.3 Implement dynamic ATR length scaling: $ATR\_Period = \max(\min\_period, \lfloor T_{dom} / 2 \rfloor)$
- [ ] 2.4 Implement Supertrend band logic using dynamic ATR and a static multiplier (default 3.0)
- [ ] 2.5 Enforce strict causality by ensuring window slices only use closed bars up to $t-1$
- [ ] 2.6 Standardize output to a binary `Indicator Score` ∈ {-1, +1} based on closing price vs. Supertrend bands

## 3. Testing and Quantitative Validation

- [ ] 3.1 Implement `test_no_lookahead()` to mathematically prove invariance when future bars $t+1...t+N$ are appended
- [ ] 3.2 Write unit tests verifying the exact binary constraint of the `Indicator Score` ∈ {-1, +1}
- [ ] 3.3 Validate the indicator correctly handles edge cases (e.g., handling the first $N$ bars before FFT stabilizes)
- [ ] 3.4 Execute `python -m pytest --cov` to guarantee comprehensive test coverage for the new signal module

## 4. Layer Integration

- [ ] 4.1 Integrate `AdaptiveFourierSupertrend` into the Layer 2 Signal Engine pipeline
- [ ] 4.2 Run Variance Inflation Factor (VIF) analysis in Layer 3 to verify the indicator maintains VIF < 10 against existing metrics
- [ ] 4.3 Verify Layer 4 (Ensemble Aggregation) correctly ingests the new feature into the L1-Lasso Logistic Regression model
- [ ] 4.4 Run a Walk-Forward Optimization (WFO) backtest pass to ensure end-to-end integration without type errors
