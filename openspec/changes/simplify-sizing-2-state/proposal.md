## Why

A separate statistical experiment proved that the current 5-state position sizing logic (`Strong Bull` -> 100%, `Weak Bull` -> 50%, else -> 0%) is too conservative and incurs a massive opportunity cost during the onset of structural bull markets. By simplifying the sizing boundary to a rigid 2-state threshold (where `Final Score >= 0.5` triggers 100% long exposure, and `< 0.5` triggers 0% cash), the backtested total return from 2016 to 2026 jumped from 2646% to 3266%. Furthermore, the risk profile remained identical, with the Max Drawdown staying at -54%. A separate experiment testing short-selling was also conducted, but the asymmetric upside of Bitcoin heavily penalized the short strategy (-76% Max Drawdown). Thus, a 2-State (Long/Cash) strategy is statistically optimal for trend-following in this regime.

## What Changes

We will modify Layer 5: Execution Engine (`src/execution/sizing.py`). The existing function `calculate_target_exposure` will be refactored to evaluate the `final_score` against a `0.5` threshold, bypassing the 5-state string evaluation for capital allocation.
- If `final_score >= 0.5`, target exposure is `1.0` (100% BTC).
- If `final_score < 0.5`, target exposure is `0.0` (100% Cash).

## Capabilities

### New Capabilities
*(None)*

### Modified Capabilities
- `execution-sizing`: The core position sizing strategy is shifting from a 5-tier gradual scale to a binary 2-state allocation (100% Long or 0% Cash).

## Impact

**Affected Code / Architecture Layer:**
- **Layer 5 (Execution Engine):** `src/execution/sizing.py` will be fundamentally simplified.

**Backtest Impact Estimates:**
Based on the combinatorial walk-forward experiment (2016-2026):
- **Total Return:** Expected to increase from ~2646% to ~3266%.
- **Sharpe Ratio:** Expected to remain extremely stable (~1.05).
- **Max Drawdown:** Expected to remain stable at ~-54.15%.

**Data Dependencies:**
- This change introduces NO new data dependencies. It purely acts on the already computed `final_score`.
