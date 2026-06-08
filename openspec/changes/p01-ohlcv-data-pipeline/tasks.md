## 1. Core Structures and Abstract Base Classes

- [x] 1.1 Create `src/data/` module and `ExchangeAdapter` abstract base class
- [x] 1.2 Define SQLite database configuration for WAL mode and OHLCV table schema
- [x] 1.3 Implement environment variable parsing for `BTC_DATA_SOURCE` and `EXCHANGE_API_KEY`

## 2. Causal Validation and Data Formatting

- [x] 2.1 Implement `pandas.DataFrame` index standardization to exactly 00:00:00 UTC boundary
- [x] 2.2 Implement strict chronological order validation (raise `ValueError` if unsorted)
- [x] 2.3 Implement index continuity validation and forward-fill logic (Close ffill, Volume 0.0)
- [x] 2.4 Write `test_no_lookahead` unit test framework ensuring causal forward-filtering constraints

## 3. Ingestion and Caching Logic

- [x] 3.1 Implement a concrete REST-based ExchangeAdapter for daily BTC OHLCV fetching
- [x] 3.2 Add exponential backoff and retry logic to the ExchangeAdapter
- [x] 3.3 Implement SQLite historical caching logic (save and load `pandas.DataFrame`)
- [x] 3.4 Implement delta fetch logic (query local SQLite for max `t`, fetch `t` to present from adapter)

## 4. Integration and Final Testing

- [x] 4.1 Create the main `ohlcv_pipeline` function that coordinates fetching, standardizing, caching, and validating
- [x] 4.2 Add `pytest` test for missing daily bar scenario (verifying ffill and 0 volume)
- [x] 4.3 Add `pytest` test for caching behavior (verifying it only fetches delta on subsequent runs)
