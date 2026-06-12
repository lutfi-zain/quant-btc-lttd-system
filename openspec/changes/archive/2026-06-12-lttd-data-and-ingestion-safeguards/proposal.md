## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->
The current data ingestion and signal engine layers contain several critical reliability issues:
1. **Ignored Dynamic Windows:** `KalmanRSI` and `AdvancedStochastic` ignore the dynamic lookbacks computed by Layer 1 and Layer 3, violating the adaptive window system.
2. **Inaccurate Stamp Ingestion:** The BRK Fetcher retrieves the global sync status update time instead of the series-specific update stamp, breaking the on-chain staleness check.
3. **Primary Key Violations in Cache:** The daily pipeline raises SQLite primary key constraints on duplicate OHLCV appends, breaking idempotency.
4. **VWMA Volume Degradation:** In some data backfills, volume is set to a constant 1.0, turning the Volume-Weighted Moving Average (VWMA) into a simple moving average.

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->
1. **Dynamic Lookback Integration:** Integrate the `_resolve_lookback()` mechanism in the compute loops of `KalmanRSI` and `AdvancedStochastic` to adapt their windows dynamically.
2. **Series-Specific Timestamp Lookup:** Retrieve timestamps from the series-specific endpoints (`/api/series/{name}/day/latest`) instead of the global sync endpoint.
3. **Upsert for Cache Persistence:** Convert the database caching append operation to use `INSERT OR REPLACE` or handle duplicates gracefully.
4. **Volume Ingestion Correction:** Ensure the pipeline and backfill scripts ingestion paths fetch and preserve correct transaction volume data.

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Replace <name> with kebab-case identifier (e.g., user-auth, data-export, api-rate-limiting). Each creates specs/<name>/spec.md -->

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
- `dynamic-signal-windows`: Bind indicator periods directly to the dynamically resolved lookback.
- `brk-ingestion-sync`: Update the BRK client fetch timestamp logic to be series-specific.
- `ohlcv-ingestion`: Support idempotent inserts in the cache database.

## Impact

<!-- Affected code, APIs, dependencies, systems -->
- **Files Modified:**
  - [kalman_rsi.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/signals/kalman_rsi.py)
  - [advanced_stochastic.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/signals/advanced_stochastic.py)
  - [brk_fetcher.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/data/brk_fetcher.py)
  - [db.py](file:///run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/src/data/db.py)
- **APIs Affected:** None.
- **Backtest Impact:** Technical indicators will react to HMM regime volatility and OU half-life updates, and the caching pipeline will run reliably.
