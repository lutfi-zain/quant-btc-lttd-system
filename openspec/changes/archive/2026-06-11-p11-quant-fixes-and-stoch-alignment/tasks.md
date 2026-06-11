## 1. Technical Indicator Realignment

- [x] 1.1 Modify `src/signals/advanced_stochastic.py` to implement the statical 1..129 For-Loop vectorized formula
- [x] 1.2 Run unit tests for AdvancedStochastic (`python3 -m pytest tests/signals/test_advanced_stochastic.py`) and verify zero lookahead bias

## 2. Regime Detection Layer Update

- [x] 2.1 Update daily pipeline in `src/pipeline.py` to use genuine Argmax for final regime classification
- [x] 2.2 Update backtest fold iterator in `src/backtest/runner.py` to use genuine Argmax for final regime classification

## 3. Integration Testing & Backtest Validation

- [x] 3.1 Run full Python unit test suite (`python3 -m pytest -xvs`) to ensure no regression
- [x] 3.2 Run the walk-forward backtest runner (`python3 -m src.backtest.runner --ensemble-mode pca_consensus`) and verify total return improves to >220% and Sharpe ratio improves
- [x] 3.3 Backfill the SQLite database with the updated historical records using the backfill script
- [x] 3.4 Verify the backend Hono API and React frontend display the updated telemetry data correctly
