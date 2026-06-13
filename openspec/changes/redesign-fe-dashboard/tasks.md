## 1. Design System Generation

- [x] 1.1 Use the Stitch MCP (`stitch-design-taste`) to generate a premium, dark-mode design system.
- [x] 1.2 Export the generated design tokens (colors, typography, spacing) into `frontend/src/index.css` as CSS variables.

## 2. Layout Infrastructure

- [x] 2.1 Refactor the main application wrapper (`frontend/src/App.tsx` or similar) to use a CSS Grid "bento-box" layout.
- [x] 2.2 Create structural placeholder containers for the top row (Macro Regime, Final Score), middle row (Chart), and bottom row (Feature Heatmap).

## 3. Component Implementation

- [x] 3.1 Implement the `HMMRegimeWidget` component to display Bull/Bear/Sideways state and posterior probability.
- [x] 3.2 Implement the `FinalScoreGauge` component to visualize the -1.0 to +1.0 ensemble score.
- [x] 3.3 Implement the `FeatureHeatmap` component to display orthogonalized indicator scores in a dense grid.

## 4. Charting Integration

- [x] 4.1 Update the TradingView Lightweight Charts initialization logic to read from the newly injected CSS variables.
- [x] 4.2 Validate that the chart background, grid lines, and fonts match the Stitch design system exactly.

## 5. Final Integration

- [x] 5.1 Connect real data endpoints from the Hono API to the new components.
- [x] 5.2 Perform visual QA against the institutional dashboard goals (high contrast, readability, spacing).
