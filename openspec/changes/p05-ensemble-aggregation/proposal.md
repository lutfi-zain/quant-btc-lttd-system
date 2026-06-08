## Why

Simple averaging of highly correlated technical indicators (VIF > 10) inflates model confidence and leads to synchronized failure during market regime shifts. Implementing an L1-Lasso Logistic Regression trained via Walk-Forward Optimization (WFO) on PCA-orthogonalized features statistically resolves this multicollinearity, prevents overfitting to obsolete market regimes, and ensures robust dynamic weighting of the final ensemble score.

## What Changes

- Implement PCA orthogonalization and Variance Inflation Factor (VIF) pruning (threshold > 10) in the Feature Processing layer to eliminate multicollinearity among technical indicators.
- Implement an L1-Lasso Logistic Regression model in the Ensemble Aggregation layer to predict the Final Score ∈ [-1.0, +1.0] dynamically.
- Integrate a Walk-Forward Optimization (WFO) pipeline utilizing Combinatorial Purged Cross-Validation (CPCV) (train 3yr → validate 6mo → test 6mo, rolling) to avoid lookahead bias and static over-fitting.
- Compute Pratt's Measure (`dⱼ = βⱼ · rⱼ / R²`) to evaluate relative indicator importance after controlling for collinearity, allowing for the pruning of redundant features.
- **Backtest Impact**: Expected to significantly reduce maximum drawdown by preventing synchronized indicator failure, and improve the overall Sharpe ratio through continuous adaptation to shifting structural regimes.
- **Data Dependency**: No new external APIs or data sources are introduced; this change strictly consumes the existing causal indicator scores produced by Layer 2.

## Capabilities

### New Capabilities
- `feature-processing`: Handles VIF computation, pruning of highly collinear indicators, and PCA orthogonalization of the incoming signal matrix.
- `ensemble-aggregation`: Manages the WFO-trained L1-Lasso Logistic Regression model to output the final weighted score, and calculates Pratt's Measure for component evaluation.
- `walk-forward-optimization`: Coordinates the rolling CPCV train-validate-test windows to ensure statistically sound out-of-sample model evaluation without data leakage.

### Modified Capabilities

## Impact

- **Architecture Layers**: Directly implements Layer 3 (Feature Processing) and Layer 4 (Ensemble Aggregation), strictly consuming from Layer 2 (Signal Engine) and outputting to Layer 5 (Execution Engine).
- **Code & Dependencies**: Relies heavily on `scikit-learn` and `pandas` for PCA, logistic regression, and cross-validation pipelines.
- **Statistical Model**: Eradicates the legacy simple averaging pattern. Enforces strict orthogonality before aggregation, transforming raw `{-1, +1}` indicator votes into a probabilistically bounded `[-1.0, +1.0]` Final Score.
