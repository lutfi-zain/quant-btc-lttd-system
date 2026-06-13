## Context

The current frontend of the `quant-btc-lttd-system` lacks the institutional-grade presentation necessary to monitor the outputs of the 5-layer LTTD pipeline. To emulate the high-end, data-dense look of Swissblock or Capriole Investments dashboards, we need a complete frontend redesign. This involves generating and applying a cohesive design system (typography, colors, grid layout) and implementing specialized widgets for Regime states, LTTD scores, and feature importance.

## Goals / Non-Goals

**Goals:**
- Implement a premium, dark-mode first design system using the Stitch MCP.
- Create specialized dashboard widgets for HMM Regime Probabilities, Final LTTD Score, and Feature Importance.
- Ensure the UI efficiently conveys quantitative data without visual clutter.
- Maintain compatibility with existing Hono v4 backend endpoints.

**Non-Goals:**
- Modifying any backend logic, database schemas, or quantitative models (Layers 1-5).
- Changing the charting library (TradingView Lightweight Charts will still be used, but styled to match the new design system).

## Decisions

1. **Design System Generation via Stitch MCP:**
   - *Rationale:* Using the Stitch MCP (`stitch-design-taste`) ensures we get a statistically calibrated, premium design system (colors, typography, spacing) that avoids generic "AI-slop" aesthetics. It enforces tight grids and cinematic contrast suitable for a quant dashboard.
   - *Alternatives:* Manually picking colors or using an off-the-shelf Tailwind template, which often look generic and not tailored to institutional finance.

2. **Styling Approach:**
   - *Rationale:* We will use vanilla CSS (or CSS modules) integrated with the generated design tokens to ensure strict adherence to the design system and maximize rendering performance.
   - *Alternatives:* Tailwind CSS, which could lead to inconsistent spacing if not strictly controlled.

3. **Dashboard Layout Architecture:**
   - *Rationale:* A "bento-box" grid layout. Top row for macro indicators (Regime, Final LTTD Score). Middle row for primary chart (BTC price with LTTD overlay). Bottom row for component breakdowns (PCA orthogonalized features, on-chain metrics).

4. **Charting Integration:**
   - *Rationale:* TradingView Lightweight Charts will have its options customized to use the exact colors and fonts from the new design system for seamless integration.

## Risks / Trade-offs

- **[Risk] Data Density vs. Readability:** A quant dashboard needs to show a lot of data, which can become cluttered.
  - *Mitigation:* Rely heavily on the Stitch-generated spacing scales and typographic hierarchy. Use color functionally (only for signaling state changes) rather than decoratively.
- **[Risk] Charting Library Styling Limitations:** TradingView Lightweight Charts might not support all styling properties of the new design system.
  - *Mitigation:* Ensure we pass the precise CSS variable values (e.g., `#0A0A0A` for background) into the chart's initialization config.
