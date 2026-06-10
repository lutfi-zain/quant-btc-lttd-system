## 1. Fractal Dimension Index (FDI) Implementation

- [x] 1.1 Create `FDI` class in `src/signals/fdi.py` inheriting from `CausalFilter`.
- [x] 1.2 Implement rolling Sevcik's algorithm for causal FDI calculation using vectorized NumPy strided arrays.
- [x] 1.3 Add logic to combine continuous FDI $D$ score with a causal baseline (EMA) and a $1.45 - 1.55$ hysteresis band to generate discrete $\{-1, +1\}$ outputs.
- [x] 1.4 Write `test_no_lookahead()` and basic functionality tests in `tests/signals/test_fdi.py` to verify zero data leakage.

## 2. Quantile DEMA Trend Implementation

- [x] 2.1 Create `QuantileDEMA` class in `src/signals/quantile_dema.py` inheriting from `CausalFilter`.
- [x] 2.2 Implement logic to extract rolling causal quantiles (e.g., 10th and 90th percentiles) from the closing price distribution.
- [x] 2.3 Implement the DEMA operator ($2 \times \text{EMA} - \text{EMA}(\text{EMA})$) over the extracted causal quantiles to form asymmetric trend bands.
- [x] 2.4 Add threshold breakout logic to output `+1` on upper quantile breakouts and `-1` on lower quantile breakouts.
- [x] 2.5 Write `test_no_lookahead()` and basic functionality tests in `tests/signals/test_quantile_dema.py` to verify zero data leakage.

## 3. Advanced Stochastic Oscillator Implementation

- [x] 3.1 Create `AdvancedStochastic` class in `src/signals/advanced_stochastic.py` inheriting from `CausalFilter`.
- [x] 3.2 Implement a dynamically adjusting lookback window calculation scaled by a causal volatility measure (ATR).
- [x] 3.3 Calculate $\%K$ and apply causal EMA smoothing to create the $\%D$ signal line.
- [x] 3.4 Add bounded exhaustion directional logic to trigger `+1` for oversold crossover reversals and `-1` for overbought crossover reversals.
- [x] 3.5 Write `test_no_lookahead()` and basic functionality tests in `tests/signals/test_advanced_stochastic.py` to verify zero data leakage.

## 4. Integration and Validation

- [x] 4.1 Register the new `FDI`, `QuantileDEMA`, and `AdvancedStochastic` indicators in the Layer 3 feature matrix builder.
- [x] 4.2 Validate that VIF metrics remain $< 10$ across the full feature matrix, and ensure Pratt's Measure pruning activates if severe multicollinearity is detected prior to PCA orthogonalization.
- [x] 4.3 Run the full validation suite (`python -m pytest --cov`) to verify integration, verify WFO pipeline compatibility, and ensure all tests pass.
