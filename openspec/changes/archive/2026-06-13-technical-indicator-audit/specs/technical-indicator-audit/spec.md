## ADDED Requirements

### Requirement: technical-indicator-range-bounds
All Layer 2 technical indicators (KalmanRSI, FDI, AdaptiveFourierSupertrend, QuantileDEMA, AdvancedStochastic, TrendStrengthIndex) SHALL return continuous or discrete values that are strictly bounded within the range $[0.0, 1.0]$.

#### Scenario: check-indicator-output-bounds
- **WHEN** computing indicator scores on the historical daily BTC price dataset
- **THEN** every computed score value $S_t$ must satisfy $0.0 \leq S_t \leq 1.0$ and the number of NaN values after the initialization period (first 350 bars) must be zero.

---

### Requirement: technical-indicator-causality-invariance
All technical indicators SHALL act as causal filters, referencing only historical and current observations (index $\leq t$). No future information or symmetric lookaheads are permitted.

#### Scenario: test-no-lookahead-empirical
- **WHEN** indicator scores are computed on the full series $X_{1 \dots T}$ yielding $S_{1 \dots T}$, and computed on the truncated series $X_{1 \dots t}$ yielding $S'_{1 \dots t}$ for any $t \in [350, T]$
- **THEN** the values must match exactly: $S_t = S'_t$ (tolerance of $10^{-9}$ for floating point precision).

---

### Requirement: stationarity-adf-testing
The statistical audit SHALL run the Augmented Dickey-Fuller (ADF) unit root test on each indicator's historical score series to evaluate stationarity.

#### Scenario: run-stationarity-adf-test
- **WHEN** the audit pipeline is executed on the historical daily BTC indicator series
- **THEN** it must calculate the ADF statistic, p-value, and critical values (1%, 5%, 10%) for each of the 6 indicators.

---

### Requirement: multicollinearity-vif-analysis
The statistical audit SHALL calculate Variance Inflation Factor (VIF) and pairwise correlations to quantify redundant momentum/trend information in the feature matrix.

#### Scenario: run-multicollinearity-vif-test
- **WHEN** the audit pipeline builds the feature matrix of the 6 indicators
- **THEN** it must compute the VIF score for each indicator and output the pairwise Pearson correlation matrix.

---

### Requirement: predictive-power-information-coefficient
The statistical audit SHALL calculate the Information Coefficient (IC) using linear (Pearson) and rank (Spearman) correlations to establish baseline predictive significance.

#### Scenario: run-predictive-power-ic-test
- **WHEN** comparing indicator scores at time $t$ against future forward log returns $R_{t \to t+k}$ for horizons $k \in \{1, 5, 10, 20\}$
- **THEN** it must output Pearson correlation, Spearman rank correlation, and their associated p-values for each indicator and horizon.

---

### Requirement: descriptive-statistics-and-reporting
The statistical audit SHALL output a formatted markdown report detailing all tests and metrics.

#### Scenario: generate-audit-report-markdown
- **WHEN** the audit execution completes
- **THEN** a formatted markdown file must be created at `docs/indicator_audit_report.md` containing summary statistics (mean, standard deviation, skewness, kurtosis), ADF statistics, VIF scores, and IC correlation tables.
