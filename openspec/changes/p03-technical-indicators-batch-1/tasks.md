## 1. Core Framework

- [x] 1.1 Create `src/signals/` directory structure and `__init__.py` files
- [x] 1.2 Implement `CausalFilter` abstract base class in `src/signals/base.py` defining the `compute(ohlcv: pd.DataFrame) -> pd.Series` interface
- [x] 1.3 Create `test_no_lookahead` unit test utility in `tests/signals/test_causality.py` to systematically verify causal constraints

## 2. Kalman RSI Implementation

- [x] 2.1 Implement `KalmanRSI` indicator in `src/signals/kalman_rsi.py` capturing hidden momentum state
- [x] 2.2 Write unit tests for `KalmanRSI` ensuring outputs are strictly `{-1, +1}` and pass `test_no_lookahead`

## 3. Adaptive Fourier Supertrend Implementation

- [x] 3.1 Implement `AdaptiveFourierSupertrend` in `src/signals/fourier_supertrend.py` using a rolling STFT to extract cycle frequencies
- [x] 3.2 Write unit tests for `AdaptiveFourierSupertrend` to validate spectral extraction and pass causality test

## 4. Trend Strength Index Implementation

- [x] 4.1 Implement `TrendStrengthIndex` in `src/signals/trend_strength.py` based on VWMA-ATR normalized distance
- [x] 4.2 Write unit tests for `TrendStrengthIndex` ensuring robust volume-adjusted signals and zero lookahead bias

## 5. Orthogonality & Integration Verification

- [x] 5.1 Implement a VIF analysis test in `tests/signals/test_vif.py` generating indicator scores over sample BTC data
- [x] 5.2 Verify that the computed Variance Inflation Factor (VIF) is `< 10` across all three indicators to confirm orthogonality
- [x] 5.3 Run `python -m pytest --cov` to ensure 100% test completion and robust coverage of the Layer 2 Signal Engine
