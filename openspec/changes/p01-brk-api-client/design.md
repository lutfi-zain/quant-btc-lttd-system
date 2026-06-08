## Context

The legacy Long-Term Trend Direction (LTTD) system implementation hardcoded historical on-chain metrics (such as STH-MVRV and STH-NUPL) into static arrays. While this allowed initial backtesting without external dependencies, it fundamentally breaks real-time live execution by silently returning `0` values for any date beyond the hardcoded array limits. 

To maintain statistical validity during out-of-sample live execution and accurately inform the Walk-Forward Optimization (WFO) pipeline, the system must pull these metrics dynamically. We will implement an external data adapter using the open-source `brk-client` to fetch data from the `bitview.space` API (Bitcoin Research Kit).

## Goals / Non-Goals

**Goals:**
- Implement a `BRKDataFetcher` interface in Layer 2 (Signal Engine) to fetch daily on-chain metrics (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`).
- Support bulk historical fetches for Walk-Forward Optimization (WFO) in Layer 4 and regime detection in Layer 1.
- Support single "latest" fetches for real-time inference in Layer 5 (Execution Engine).
- Enforce strict freshness validation on the `stamp` field returned by the API (must be `>= current_date - 1 day`).

**Non-Goals:**
- Adding authentication or rate-limiting handling for the BRK API (the endpoint is public, free, and does not require an API key).
- Replacing standard OHLCV price data with BRK price data (price data will continue to come from the primary exchange data source configured via `BTC_DATA_SOURCE`).
- Real-time tick-level fetching (all BRK endpoints used are daily indices).

## Decisions

**1. Data Client Abstraction (Domain Adapter Pattern)**
- *Decision*: We will wrap the raw `brk-client` in a project-specific `BRKDataFetcher` class rather than using the raw client directly across layers.
- *Rationale*: Isolates the external dependency. If the BRK API schema changes or we migrate to a local node in the future, only the fetcher class needs updating.
- *Alternatives*: Calling `brk-client` directly in the signal processors. Rejected because it litters API specifics (like handling the `stamp` and `data` dictionary structure) throughout the signal generation logic.

**2. Freshness Validation Strategy**
- *Decision*: The `BRKDataFetcher` will implement a strict assertion: `assert brk_feed.stamp >= current_date - timedelta(days=1)`. If stale data is detected during live inference, it will raise a `StaleOnChainDataError`.
- *Rationale*: On-chain data is derived from settled blocks. BRK provides end-of-day daily indices. Trading on data that is multiple days old destroys the causal alignment of the indicators. Halting is safer than executing on stale metrics.
- *Alternatives*: Forward-filling stale data. Rejected because it introduces synthetic stagnation into the HMM regime detector, potentially causing false positive regime transitions.

**3. Bulk vs. Latest Endpoint Usage**
- *Decision*: Use `/api/series/bulk?index=day&series=...` for backtesting and WFO training pipelines. Use `/api/series/{name}/day/latest` for real-time daily inference.
- *Rationale*: Optimizes network I/O and memory. WFO requires deep historical matrices, whereas the daily cron only needs the most recent confirmed state.

**4. Data Alignment with OHLCV**
- *Decision*: On-chain data fetched via BRK will be joined to the primary OHLCV DataFrame using the `stamp` index (UTC date). Missing historical dates will be forward-filled (`ffill()`) up to a maximum of 1 day to account for minor block parsing delays.
- *Rationale*: The daily price candle close and the daily on-chain aggregation window must align to prevent lookahead bias.

## Risks / Trade-offs

- **[Risk] BRK API Downtime / Unavailability**: Since the bitview.space API is a free community resource, it may face downtime.
  - *Mitigation*: The `StaleOnChainDataError` will bubble up to the Execution Engine, which will pause that day's LTTD update and alert the user, maintaining the previous day's state in the SQLite WAL.
- **[Risk] OHLCV Timestamp Misalignment**: Exchange OHLCV data might close at 00:00 UTC, while BRK data might index differently.
  - *Mitigation*: Explicitly normalize all joining keys to `YYYY-MM-DD` string formats or tz-naive `datetime.date` objects before merging the DataFrames.

## Migration Plan

1. Add `brk-client` to `requirements.txt`.
2. Implement `BRKDataFetcher` in a new module (e.g., `src/data/brk_fetcher.py` or integrated into `src/signals/onchain.py`).
3. Replace `F1_data`...`F4_data` usages in `src/signals/` with calls to the new fetcher.
4. Run `test_no_lookahead()` to ensure the newly integrated data respects causality.
5. Execute a full backtest (`python -m pytest --cov` and `python -m src.backtest.runner`) to verify that historical outputs match legacy backtest results up to the hardcoded date limit.

## Open Questions

- Should the system cache historical bulk BRK data in a local SQLite table (`database/brk_cache.db`) to speed up repeated WFO runs during research, or always fetch fresh on startup? *(Recommendation: In-memory fetch is fast enough for now; caching can be added later if WFO iterations become bottlenecked.)*
