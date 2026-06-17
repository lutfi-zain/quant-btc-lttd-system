## Context

The current LTTD Execution Engine (Layer 5) utilizes a 5-state categorical regime string (`Strong Bull`, `Weak Bull`, `Neutral`, `Weak Bear`, `Strong Bear`) mapped from the `final_score` to determine the target BTC exposure (ranging from 0.0 to 1.0). Statistical backtesting via combinatorial Walk-Forward Optimization (WFO) has demonstrated that this gradual scaling approach (e.g., 50% exposure at `Weak Bull`) causes significant opportunity costs at the onset of major bull cycles. A binary 2-state strategy (100% exposure if `final_score >= 0.5`, otherwise 0%) yields a dramatically higher total return (+~600% absolute difference over 10 years) with nearly identical max drawdown and Sharpe ratio.

## Goals / Non-Goals

**Goals:**
- Refactor the execution logic in `src/execution/sizing.py` to use a direct numeric threshold against `final_score`.
- Convert the capital allocation curve from a 5-step ladder to a binary step function at `0.5`.
- Preserve the calculation of `final_score` and the legacy regime string strictly for logging and telemetry purposes.

**Non-Goals:**
- Modifying the underlying feature aggregation (Layer 4).
- Adding or modifying technical or on-chain indicators (Layers 2 & 3).
- Implementing short-selling (exposure < 0), as experiments proved it heavily penalizes performance in the crypto asset class.

## Decisions

**1. Direct Numeric Thresholding over Categorical Mapping**
Instead of mapping `final_score` $\to$ `regime string` $\to$ `target_exposure`, the function `calculate_target_exposure(final_score: float, regime: str)` will directly evaluate `final_score >= 0.5`.
*Rationale:* Removes unnecessary indirection and completely decouples the exact allocation logic from the arbitrary textual labels used for logging.
*Alternatives Considered:* Retaining the 5-state strings but mapping `Weak Bull` to `1.0`. Rejected because it creates a conceptual mismatch (why would "Weak" imply 100% conviction?). Numeric thresholding is cleaner mathematically.

**2. Retaining the `regime` Argument in Signature**
The signature `calculate_target_exposure(final_score: float, regime: str)` will be preserved, but the logic inside will ignore `regime` (or only use it as a fallback if `final_score` is somehow None, though strictly typed as float).
*Rationale:* Ensures zero breakages in upstream callers (like `BacktestRunner` or live execution adapters) that already pass both arguments.

## Risks / Trade-offs

- **[Risk] Increased Turnover (Whipsaw):** A strict threshold at 0.5 might cause the system to rapidly flip between 100% and 0% if the score hovers exactly around 0.5 for several days.
  $\to$ *Mitigation:* The `final_score` is already heavily smoothed by the causal EMA in the signals and the robust PCA consensus layer. Empirically, the WFO results showed no degradation in Sharpe ratio (1.05), indicating whipsaw transaction costs are negligible compared to the trend capture gains.
