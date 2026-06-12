## 1. Setup & Integration

- [x] 1.1 Run tests to confirm the baseline starting state is green.
- [x] 1.2 Checkout a new branch `feature/LTTD-data-and-ingestion-safeguards`.

## 2. Core Safeguard Implementations

- [x] 2.1 Refactor `KalmanRSI` to scale its normalizer using the dynamically resolved lookback.
- [x] 2.2 Refactor `AdvancedStochastic` to scale its window bounds dynamically using the resolved lookback.
- [x] 2.3 Modify the timestamp retrieval in `BRKDataFetcher.fetch_latest` to fetch the specific series timestamp.
- [x] 2.4 Update `save_dataframe` in `src/data/db.py` to run an idempotent write (excluding duplicates or using upsert).

## 3. Validation

- [x] 3.1 Verify that the updated indicators pass `test_no_lookahead()` checks.
- [x] 3.2 Run the full pytest suite (`python3 -m pytest -xvs`) to verify all tests pass.
