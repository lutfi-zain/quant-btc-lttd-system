## 1. Setup & Data Ingestion

- [x] 1.1 Verify historical daily BTC OHLCV dataset is available in database via ohlcv_pipeline
- [x] 1.2 Establish indicator computation pipeline inside the audit script to load and compute scores for FDI, AdvancedStochastic, KalmanRSI, FourierSupertrend, TrendStrengthIndex, and QuantileDEMA

## 2. Statistical Testing Implementation

- [x] 2.1 Implement Augmented Dickey-Fuller (ADF) stationarity test logic using statsmodels
- [x] 2.2 Implement Variance Inflation Factor (VIF) and pairwise correlation metrics using pandas and statsmodels
- [x] 2.3 Implement Information Coefficient (IC) calculations (Pearson and Spearman) against forward returns (1d, 5d, 10d, 20d)
- [x] 2.4 Implement strict causality (lookahead bias) validation that truncates datasets and asserts identical output

## 3. Execution & Report Generation

- [x] 3.1 Run the statistical audit script on the historical BTC daily dataset
- [x] 3.2 Generate the comprehensive Markdown report at `docs/indicator_audit_report.md`
- [x] 3.3 Create test cases in the test suite to execute the causality invariance verification automatically
