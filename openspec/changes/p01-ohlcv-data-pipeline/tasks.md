## 1. Core Structures and Abstract Base Classes

- [ ] 1.1 Create `src/data/` module and `ExchangeAdapter` abstract base class
- [ ] 1.2 Define SQLite database configuration for WAL mode and OHLCV table schema
- [ ] 1.3 Implement environment variable parsing for `BTC_DATA_SOURCE` and `EXCHANGE_API_KEY`

## 2. Causal Validation and Data Formatting

- [ ] 2.1 Implement `pandas.DataFrame` index standardization to exactly 00:00:00 UTC boundary
- [ ] 2.2 Implement strict chronological order validation (raise `ValueError` if unsorted)
- [ ] 2.3 Implement index continuity validation and forward-fill logic (Close ffill, Volume 0.0)
- [ ] 2.4 Write `test_no_lookahead` unit test framework ensuring causal forward-filtering constraints

## 3. Ingestion and Caching Logic

- [ ] 3.1 Implement a concrete REST-based ExchangeAdapter for daily BTC OHLCV fetching
- [ ] 3.2 Add exponential backoff and retry logic to the ExchangeAdapter
- [ ] 3.3 Implement SQLite historical caching logic (save and load `pandas.DataFrame`)
- [ ] 3.4 Implement delta fetch logic (query local SQLite for max `t`, fetch `t` to present from adapter)

## 4. Integration and Final Testing

- [ ] 4.1 Create the main `ohlcv_pipeline` function that coordinates fetching, standardizing, caching, and validating
- [ ] 4.2 Add `pytest` test for missing daily bar scenario (verifying ffill and 0 volume)
- [ ] 4.3 Add `pytest` test for caching behavior (verifying it only fetches delta on subsequent runs)
