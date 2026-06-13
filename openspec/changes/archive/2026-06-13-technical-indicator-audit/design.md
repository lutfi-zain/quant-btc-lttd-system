## Context

We are conducting a comprehensive statistical audit of all 6 technical indicators in Layer 2 (Signal Engine):
1. **KalmanRSI**
2. **FDI** (Fractal Dimension Index)
3. **AdaptiveFourierSupertrend**
4. **QuantileDEMA**
5. **AdvancedStochastic**
6. **TrendStrengthIndex**

This audit will ensure that:
- Features are strictly causal (zero lookahead bias).
- Features are stationary (allowing stable, non-spurious coefficients in downstream models).
- Multicollinearity is identified and handled (using Variance Inflation Factor).
- Indicators have verified predictive power (measured using the Information Coefficient).
- Indicator outputs conform to $[0.0, 1.0]$ bounds.

## Goals / Non-Goals

**Goals:**
- Implement a statistical audit script (`scripts/indicator_statistical_audit.py`) that executes statistical tests on all 6 indicators over the historical daily BTC OHLCV dataset.
- Run Augmented Dickey-Fuller (ADF) tests to measure stationarity.
- Run Variance Inflation Factor (VIF) tests to measure multicollinearity.
- Run Pearson and Spearman Rank correlation tests against future log returns (1d, 5d, 10d, 20d horizons) to calculate the Information Coefficient (IC).
- Verify causality by implementing a test suite checking that appending future bars doesn't change historical output.
- Generate a comprehensive markdown report (`docs/indicator_audit_report.md`) detailing the findings.

**Non-Goals:**
- Rewriting or modifying the mathematical formulas of the technical indicators (unless the audit exposes bugs or lookahead bias).
- Implementing new trading execution logic or changing the ensemble models themselves.
- Integrating external paid on-chain data providers (only the free BRK/bitview.space client is used).

## Decisions

### 1. Ingestion and Setup
- **Decision**: Load historical price data using the existing `ohlcv_pipeline()` function from `src.data.pipeline`, which handles database caching (`ohlcv` table in `database/lttd.db`) and Binance adapter fetching.
- **Rationale**: Reuses production data access pipelines, ensuring consistency with live execution data.

### 2. Statistical Analysis Framework
- **Decision**: Use `statsmodels.tsa.stattools.adfuller` for ADF test, `statsmodels.stats.outliers_influence.variance_inflation_factor` for VIF, and `scipy.stats.pearsonr` / `scipy.stats.spearmanr` for Information Coefficients.
- **Rationale**: Industry-standard, production-grade statistical libraries that are already available in the Python execution environment.
- **Alternatives Considered**: Writing custom stats functions from scratch. Rejected due to complexity, lack of performance optimization, and risk of bugs.

### 3. Verification of Zero Lookahead Bias (Causality Test)
- **Decision**: Write a systematic causality check in the audit script that computes the indicator on the full dataset, then computes it on a truncated dataset (up to $t$), and asserts that the outputs at $t$ are identical.
- **Rationale**: Empirically proves that no future data (e.g., symmetric windows, future shifts, lookahead indices) is leaked into current/historical signal computations.

### 4. Variance Inflation Factor (VIF) Pruning & PCA Configuration
- **Decision**: Report individual VIF scores for the 6 technical indicators. We will verify how VIF changes when including on-chain metrics (using the 85% explained variance threshold for CausalPCA in Layer 3).
- **Rationale**: Aligns with the Layer 3 `FeatureProcessor` design which runs VIF pruning at a threshold of 10.0 and applies PCA to the remaining technical indicators.

## Risks / Trade-offs

- **[Risk] Spurious correlation with long-term forward returns** → Mitigation: Use both short-term (1d) and medium-term (5d, 10d, 20d) forward return horizons and evaluate Spearman rank correlation (Spearman is robust to outliers and non-linear monotonic relationships).
- **[Risk] High collinearity among momentum/trend indicators** → Mitigation: Identify high VIF indicators (VIF > 10.0) in the report and recommend they continue to be processed via PCA orthogonalization in Layer 3.
