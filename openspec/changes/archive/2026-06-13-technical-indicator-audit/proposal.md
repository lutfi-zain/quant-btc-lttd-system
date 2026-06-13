## Why

To ensure the statistical integrity and live trading robustness of the LTTD (Long-Term Trend Direction) trading system, we must conduct a comprehensive, production-grade statistical audit of all Layer 2 technical indicators:
1. **KalmanRSI**
2. **FDI** (Fractal Dimension Index)
3. **AdaptiveFourierSupertrend**
4. **QuantileDEMA**
5. **AdvancedStochastic**
6. **TrendStrengthIndex**

In algorithmic trading, relying on unverified price features leads to overfitting, lookahead bias, and synchronized failures due to multicollinearity. This audit provides empirical validation of:
- **Causality / Lookahead Bias**: Verifying that indicator scores at time $t$ are invariant to future data updates ($t+1..t+N$), ensuring zero lookahead bias.
- **Multicollinearity (VIF)**: Checking the Variance Inflation Factor (VIF) and pairwise correlations of all indicators. High VIF ($>10$) inflates the variance of ensemble coefficients, causing model instability.
- **Stationarity**: Standard machine learning models assume stationary inputs. We must apply the Augmented Dickey-Fuller (ADF) test to ensure indicators do not contain unit roots.
- **Predictive Power (Information Coefficient)**: Measuring the linear (Pearson) and monotonic (Spearman Rank) correlation between indicator scores at time $t$ and future forward returns $R_{t \to t+k}$ (for $k \in \{1, 5, 10, 20\}$) to establish baseline predictive power.
- **Range & Scaling Compliance**: Confirming that all indicators output values strictly bounded in $[0.0, 1.0]$.

## What Changes

We will introduce a production-grade statistical audit pipeline:
1. Create `scripts/indicator_statistical_audit.py` to ingest historical daily BTC OHLCV data from the SQLite database (`database/lttd.db`), run the 6 technical indicators, and compute:
   - ADF Stationarity Tests (statistic, p-value, critical values, and stationary status).
   - VIF Multicollinearity Analysis (individual VIF scores, pairwise correlation matrix).
   - Information Coefficient (Pearson/Spearman correlation with 1d, 5d, 10d, and 20d future log returns, along with p-values).
   - Descriptive Statistics (mean, std, min, max, skewness, kurtosis, and bounds violation flags).
2. Save the final audit findings as a markdown report (`docs/indicator_audit_report.md`) containing tables and analyses of each indicator.
3. Enhance indicator test coverage to guarantee zero lookahead bias.

## Capabilities

### New Capabilities
- `technical-indicator-audit`: A pipeline and reporting mechanism to run multi-dimensional statistical validation (causality, stationarity, multicollinearity, predictive power, distribution) on all technical indicators.

### Modified Capabilities
*None*

## Impact

- **Affected Layers**: Layer 2 (Signal Engine) and Layer 3 (Feature Processing) are analyzed.
- **Data Dependencies**: None. Uses existing historical daily BTC OHLCV data from `database/lttd.db`.
- **Ensemble Stability**: The audit will directly identify indicators that suffer from multicollinearity (VIF > 10) or non-stationarity, justifying pruning or PCA orthogonalization choices in Layer 3 and stabilizing the L1-Lasso Logistic Regression weights.
- **Backtest Impact**: Prevents out-of-sample performance degradation caused by overfitting and uncovers lookahead bias before live execution.
