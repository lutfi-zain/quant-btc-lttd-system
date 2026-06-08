## Context

The LTTD (Long-Term Trend Direction) system relies heavily on the temporal integrity of price data to infer market regimes and generate trading signals. The system requires an orthogonal ensemble of causal technical indicators computed at Layer 2 (Signal Engine). To support this, we must build a robust, causal OHLCV (Open, High, Low, Close, Volume) data ingestion and processing pipeline. 

A primary constraint in quantitative trading systems is the strict elimination of lookahead bias. Any data structure or filtering algorithm that inadvertently references future data points (`t+N`) at time `t` will invalidate the backtest and fail disastrously in live trading. The OHLCV pipeline must enforce absolute causal boundaries, ensuring that data passed to Layer 2 and Layer 3 strictly respects the real-time flow of market information.

## Goals / Non-Goals

**Goals:**
- Create the `ohlcv-ingestion` module to reliably fetch daily BTC OHLCV data from exchange sources specified by the `BTC_DATA_SOURCE` environment variable.
- Implement the `causal-price-filtering` capability to validate the sequence and causality of incoming data, ensuring it is safe for Layer 2 consumption.
- Standardize the OHLCV output format into time-indexed `pandas.DataFrame` structures.
- Implement automatic handling of missing data points and timezone standardization (enforcing UTC).

**Non-Goals:**
- Implementing specific technical indicators (e.g., Kalman RSI) — this is explicitly the responsibility of Layer 2 (Signal Engine).
- Fetching or joining on-chain metrics (e.g., STH-MVRV) — this is handled by a separate integration using the `brk-client`.
- Managing execution logic or position sizing — this belongs to Layer 5 (Execution Engine).

## Decisions

### 1. Core Data Structure: Pandas DataFrames
- **Rationale**: The pipeline will output time-indexed `pandas.DataFrame` objects. Pandas provides robust native support for time-series alignment, frequency enforcement, and safe rolling window operations. It seamlessly handles missing dates and simplifies the process of orthogonalization later in Layer 3.
- **Alternatives Considered**: Raw `numpy` arrays. While computationally faster, raw arrays lack explicit datetime indices. Managing temporal alignment manually across OHLCV and on-chain datasets significantly increases the risk of misalignment and lookahead bias.

### 2. Fetching Abstraction: Exchange Adapter Pattern
- **Rationale**: We will implement an `ExchangeAdapter` abstract base class to handle data ingestion. The concrete implementation used will be driven by the `BTC_DATA_SOURCE` environment variable. This shields the pipeline from the volatility of specific exchange APIs and allows for easy swapping between data providers (e.g., from Binance to Coinbase) without altering core logic.
- **Alternatives Considered**: Direct coupling to a specific exchange's REST API or SDK (e.g., `ccxt`). Direct coupling was rejected to maintain modularity. While `ccxt` is an option, a lightweight custom adapter avoids heavy dependencies if we only require a single generic REST endpoint for daily OHLCV.

### 3. Causal Validation Strategy
- **Rationale**: To enforce the causal-only constraint, the pipeline will include a strict validation step. It will ensure data is sorted chronologically and enforce a strict daily UTC index. In testing, `pytest` fixtures will assert that operations like `shift(-1)` or symmetric window filters (like default Savitzky-Golay) raise exceptions. The pipeline will exclusively use causal forward-filtering logic (e.g., `shift(1)` for lags).
- **Alternatives Considered**: Runtime interception of array index access. Deemed overly complex and detrimental to performance. Validation via schema and unit tests is sufficient and performant.

### 4. Daily Close Boundary Standardization
- **Rationale**: Cryptocurrencies trade 24/7, but daily on-chain metrics (from BRK) are computed with a 00:00:00 UTC cutoff. The OHLCV pipeline will enforce that all ingested data aligns to the 00:00:00 UTC boundary, stripping arbitrary exchange-specific timezones. 
- **Alternatives Considered**: Accepting native exchange timestamps. Rejected because a mismatch between the OHLCV daily close and the on-chain metric daily calculation would introduce minor lead/lag errors, corrupting the feature correlation space.

## Risks / Trade-offs

- **[Risk] Exchange Rate Limits & API Downtime**: The external `BTC_DATA_SOURCE` may throttle requests or become temporarily unavailable, causing data gaps.
  - **Mitigation**: Implement robust retry logic with exponential backoff. The pipeline will also cache historical data locally in SQLite (`database/lttd.db`) so that only the delta (new bars) needs to be fetched, drastically reducing API load.
- **[Risk] Missing or Irregular Bars**: An exchange might experience an outage, resulting in missing daily bars.
  - **Mitigation**: The pipeline will enforce strict index continuity. Any missing days will be automatically forward-filled (`ffill()`) for `Close` prices, and `Volume` will be set to `0`. This preserves temporal alignment without fabricating artificial price movement.
- **[Risk] Lookahead Bias in Third-party Libraries**: `pandas` or `scipy` functions may default to non-causal behaviors (e.g., centered rolling windows).
  - **Mitigation**: Code reviews and the `test_no_lookahead()` unit test requirement defined in the architecture will ensure all transformations explicitly define right-aligned, causal parameters.
