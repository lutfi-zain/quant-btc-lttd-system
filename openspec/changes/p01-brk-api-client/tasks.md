## 1. Setup and Dependencies

- [x] 1.1 Add `brk-client` to `requirements.txt`
- [x] 1.2 Create `src/data/brk_fetcher.py` and implement the `StaleOnChainDataError` exception

## 2. BRKDataFetcher Implementation

- [x] 2.1 Implement `BRKDataFetcher.fetch_latest(series_name)` for real-time inference using the `brk-client` (targets `/api/series/{name}/day/latest`)
- [x] 2.2 Implement timestamp freshness validation in `fetch_latest` to assert `stamp >= current_date - timedelta(days=1)`, raising `StaleOnChainDataError` if stale
- [x] 2.3 Implement `BRKDataFetcher.fetch_historical_bulk(series_list, start)` for WFO training using the `brk-client` (targets `/api/series/bulk`)
- [x] 2.4 Implement `BRKDataFetcher.align_with_ohlcv(brk_df, ohlcv_df)` to join on-chain data with OHLCV using the `stamp` index and apply `ffill(limit=1)`

## 3. Signal Engine Integration

- [x] 3.1 Refactor Layer 2 (`src/signals/`) to replace legacy static array mappings (`F1_data` to `F4_data`) with calls to `BRKDataFetcher`
- [x] 3.2 Update Layer 4 (Ensemble Aggregation / WFO pipeline) to fetch deep on-chain metric matrices using `fetch_historical_bulk`
- [x] 3.3 Update Layer 5 (Execution Engine) to retrieve daily LTTD on-chain metrics using `fetch_latest`
- [x] 3.4 Implement exception handling in the Execution Engine to catch `StaleOnChainDataError` and safely pause the daily run without writing erroneous zero-values to SQLite

## 4. Testing and Validation

- [x] 4.1 Create `tests/data/test_brk_fetcher.py` with mock tests for both `fetch_latest` and `fetch_historical_bulk`
- [x] 4.2 Write a specific test verifying that `StaleOnChainDataError` is raised when the returned `stamp` is more than 1 day old
- [x] 4.3 Write a `test_no_lookahead()` test for the merged on-chain data to ensure causal alignment is strictly preserved
- [x] 4.4 Run `python -m pytest --cov` to validate changes and verify that historical outputs match legacy backtests up to the hardcoded date limits
