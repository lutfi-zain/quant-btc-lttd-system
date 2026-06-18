## Why

The current LTTD backtest produces a Sharpe Ratio of 0.4324 and Max Drawdown of -65.42%, severely underperforming buy-and-hold BTC. Our recent data science audit identified four fatal statistical flaws causing this:
1. **Dummy Variable Trap**: The HMM probabilities (`p_bull`, `p_bear`, `p_sideways`) sum to 1, causing infinite Variance Inflation Factor (VIF) and breaking linear ensemble models (probability leakage).
2. **On-Chain Multicollinearity**: `sth_mvrv` and `sth_nupl` are highly collinear (VIF > 48) and measure the same underlying factor (STH profitability).
3. **Regime Vocabulary Violation**: The HMM outputs 5 granular states (e.g., "Strong Bull", "Weak Bear") instead of the spec-mandated 3 states (`BULL`, `BEAR`, `SIDEWAYS`), fragmenting execution logic.
4. **Hit Rate Inversion**: The model achieves <50% hit rate in strong bull markets, indicating lagging causal filters or contrarian overfitting.

## What Changes

We will refactor the feature matrix generation and regime inference code to rectify these statistical anomalies.
- **Layer 1 (Regime Detection)**: Constrain or map HMM states to output exactly `BULL`, `BEAR`, or `SIDEWAYS`.
- **Layer 3 (Feature Processing)**:
  - Implement a VIF pre-filter to drop redundant on-chain metrics (e.g., keeping only `sth_mvrv` and dropping `sth_nupl`).
  - Drop the `p_sideways` probability column before passing features to the Ensemble layer to eliminate the dummy variable trap.
- **Layer 2 & 4 (Signal Engine & Ensemble)**: Review filter lengths and calibration to reduce lag causing hit-rate inversion.

## Capabilities

### New Capabilities
- `statistical-pruning`: Strict pre-ensemble multicollinearity filtering (dropping collinear on-chain metrics and redundant dummy variables).

### Modified Capabilities
- `regime-classification`: Restricting the HMM state output strictly to the defined `BULL`, `BEAR`, and `SIDEWAYS` ubiquitous language.

## Impact

**Architecture Layers Affected:** Regime (Layer 1), Feature (Layer 3), and Ensemble (Layer 4).

**Backtest Impact:**
- **Sharpe Ratio**: Expected to increase from 0.43 to > 1.2+ by removing contradictory features and probability leakage.
- **Max Drawdown**: Expected to improve from -65% to better than -40% as the model correctly identifies trending environments without lag.

**Data Dependencies:** No new data dependencies, APIs, or features are introduced. We are strictly pruning and correcting the existing feature matrix.
