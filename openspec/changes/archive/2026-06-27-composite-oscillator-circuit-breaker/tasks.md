## 1. Valuation API Client (Layer 2)

- [x] 1.1 Create `src/data/valuation_api_client.py` with a robust `requests`-based client that fetches from `http://localhost:5173/api/composite`.
- [x] 1.2 Implement caching and error handling (try/except blocks) that default to `0.0` on failure, timeout, or missing connection.
- [x] 1.3 Create unit tests in `tests/data/test_valuation_api_client.py` mocking successful and failed API responses.

## 2. Execution Circuit Breaker (Layer 5)

- [x] 2.1 Update `src/execution/sizing.py` to accept the `composite_value` state alongside the HMM regime.
- [x] 2.2 Implement the circuit breaker logic: If `composite_value <= -1.20`, set `target_exposure = 0.0`.
- [x] 2.3 Implement the cool-off logic: Maintain `0.0` until `composite_value > -0.50` is reached.
- [x] 2.4 Create unit tests in `tests/execution/test_sizing.py` verifying that the circuit breaker overrides BULL regimes and correctly resets during the cool-off phase.

## 3. Pipeline Integration

- [x] 3.1 Update `src/pipeline.py` or the main orchestrator to instantiate `ValuationApiClient` and pass the fetched composite value into the Execution Engine sizing step.
- [x] 3.2 Update `scripts/performance_report.py` (if necessary) to reflect or simulate the circuit breaker in historical backtests (which would require historical composite values, likely fetched entirely once during backfill).
- [ ] 3.3 Create a script `scripts/backfill_composite.py` to pull the full history of the composite oscillator and store it alongside the LTTD database for backtesting purposes.

## 4. Validation

- [ ] 4.1 Run full test suite (`python -m pytest --cov`).
- [ ] 4.2 Run a backtest (`python -m src.backtest.runner` or via performance report) and verify that the Max Drawdown improves (targets < -40%) compared to the baseline without the circuit breaker.
