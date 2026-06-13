## MODIFIED Requirements

### Requirement: Coherence-based Ensemble Aggregation
At the daily level, the Ensemble Aggregation layer MUST use a `CoherenceEngine` to evaluate agreement across multiple `TrendComponent` signals. The engine MUST require a configurable minimum number of components to agree before generating a trade signal. The coherence signal MUST be one of: BUY (1.0), SELL (-1.0), or HOLD (0.0).

#### Scenario: Coherence Signal Generation
- **GIVEN** daily confidence scores from N `TrendComponent` instances
- **WHEN** the `CoherenceEngine.evaluate()` method processes the component signals
- **THEN** the output coherence signal MUST be one of: 1.0 (BUY), -1.0 (SELL), or 0.0 (HOLD)
- **THEN** the confidence metric MUST be a float in `[0.0, 1.0]` representing the ratio of agreeing components

#### Scenario: Majority Agreement Threshold
- **GIVEN** 6 component signals where 4 vote BUY and 2 vote SELL
- **WHEN** the `CoherenceEngine` is configured with `mode="majority"`
- **THEN** the coherence signal MUST be 1.0 (BUY) since 4 ≥ 4 (50%+1 of 6)

### Requirement: Component Confidence Score Aggregation
Ensemble Aggregation MUST aggregate component outputs as confidence scores ∈ [0, 1] rather than directional signals ∈ {-1, +1}. Each component's confidence MUST be independently normalized before coherence evaluation.

#### Scenario: Normalized Confidence Input
- **GIVEN** raw indicator outputs from 6 `TrendComponent` instances
- **WHEN** the ensemble layer processes these outputs
- **THEN** each component's output MUST be normalized to `[0.0, 1.0]` before coherence evaluation
- **AND** the normalization MUST NOT introduce lookahead bias

## REMOVED Requirements

### Requirement: L1-Lasso Logistic Regression Ensemble
**Reason**: Replaced by CoherenceEngine voting mechanism. L1-Lasso aggregation is incompatible with [0, 1] confidence scores and regime-aware threshold logic.
**Migration**: Use `CoherenceEngine` with majority/supermajority voting mode. Component weights are determined by threshold configuration, not regression coefficients.

### Requirement: Pratt's Measure Calculation
**Reason**: Pratt's Measure requires regression-based ensemble which is being replaced by coherence voting. Importance is now determined by component threshold tuning, not statistical decomposition.
**Migration**: Component importance is managed via `buy_threshold` and `sell_threshold` configuration. Use backtest validation to tune thresholds empirically.

### Requirement: L1 Lasso Feature Selection
**Reason**: Feature selection is no longer performed at ensemble level. Components are selected based on IC analysis and VIF pruning at feature layer, not Lasso coefficient shrinkage.
**Migration**: Use VIF analysis at Layer 3 to prune redundant components. Use Information Coefficient analysis to select components with IC > 0.03.
