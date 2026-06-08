## Why

To compute technical indicators and extract quantitative trading signals, the system requires a robust and causal OHLCV (Open, High, Low, Close, Volume) data pipeline. A reliable data feed is statistically crucial because accurate, unlagged price arrays ensure that the technical indicators derived from OHLCV reflect real-time market dynamics without lookahead bias. Implementing this pipeline now is necessary to feed into Layer 2 (Signal Engine) and compute signals properly under the constraint of strictly causal filtering.

## What Changes

- Implement the core OHLCV data fetching and pre-processing pipeline for daily Bitcoin price data.
- Enforce causal-only constraints during data ingestion by validating that all references utilize past bars only to guarantee zero lookahead bias.
- Standardize the OHLCV dataset output to seamlessly integrate with Layer 2 (Signal Engine) and Layer 3 (Feature Processing).
- **BREAKING**: Any existing manual data mocks or non-causal static arrays will be replaced with validated, causal OHLCV data structures.

## Capabilities

### New Capabilities
- `ohlcv-ingestion`: Manages the retrieval and structuring of OHLCV data from the configured data source, ensuring timestamp alignment and integrity.
- `causal-price-filtering`: Standardizes and pre-processes raw OHLCV data using strictly causal transformations to maintain strict temporal ordering and eliminate lookahead bias before signal calculation.

### Modified Capabilities

- 

## Impact

- **Affected Architecture Layers**: This directly impacts Layer 2 (Signal Engine) and Layer 3 (Feature Processing), as they consume the processed OHLCV arrays to generate and orthogonalize indicators.
- **Backtest Impact**: Enforcing absolute causal filtering may slightly reduce the naive Sharpe ratio compared to models with lookahead bias, but it significantly stabilizes maximum drawdown estimates and ensures the backtest accurately reflects live execution capabilities.
- **Data Dependencies**: Introduces a new dependency on a reliable daily BTC OHLCV data source (configured via `BTC_DATA_SOURCE` and `EXCHANGE_API_KEY` environment variables).
- **Redundancy Analysis**: This pipeline is a foundational data layer rather than a single indicator. It does not overlap with on-chain metrics (STH-MVRV, etc.). It strictly provides the raw dimensions needed for computing independent price-based indicators, which will subsequently be evaluated using Variance Inflation Factor (VIF) pruning in Layer 3.
