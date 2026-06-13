## MODIFIED Requirements

### Requirement: Charting Presentation Redesign
The existing TradingView Lightweight Charts MUST be re-styled to seamlessly match the new Stitch-generated design system.

#### Scenario: Chart initialization
- **GIVEN** the `frontend-presentation` module loads the chart component
- **WHEN** the chart is instantiated
- **THEN** the chart configuration MUST use the exact background color, grid line color, and font family defined in the new design system tokens.

### Requirement: Layout Restructuring
The existing basic frontend layout MUST be replaced with a high-density "bento-box" layout typical of institutional dashboards (e.g., Swissblock, Capriole).

#### Scenario: Layout rendering
- **GIVEN** the main application wrapper
- **WHEN** the page is loaded
- **THEN** the layout MUST structure components into clear hierarchical rows/grids (Macro Regime at top, Chart in middle, Feature breakdowns at bottom), abandoning the previous linear or simple layout.

## Non-Goals
- Changing the charting library from TradingView Lightweight Charts.
- Altering the historical data fetching logic.
