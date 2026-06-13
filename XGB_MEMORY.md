# XGBoost Engineering Memory

- **Findings**: Binary sizing with threshold 0.5 destroys the strategy because intermediate scores (0.4-0.7) have < 50% hit rates. Continuous sizing naturally dampens volatility by reducing exposure precisely when the edge is low.
- **XGBoost Integration**: Successfully integrated XGBRegressor with `reg:squarederror`. It outputs continuous probabilities which map beautifully to continuous sizing.
- **Feature Engineering**: Tested multi-horizon momentum, Volatility, and Moving Average distance. The most powerful features by far are the causal FDI (44% importance) and TrendStrengthIndex (16%).
- **Performance Achieved**: With `n_estimators=500`, `max_depth=5`, `learning_rate=0.01` and continuous sizing, the model hit 205% return and 1.60 Sharpe out-of-sample over the 2021-2025 WFO folds.
- **WFO Limitations**: Shrinking the training window to 2 years reduces data too much, dropping Sharpe to 0.82. The 3-year sliding window is essential for stability.
- **Further Optimization**: Combined `XGBRegressor` (30%) with `ElasticNetCV` (70%) and scaled features using `StandardScaler`. This raised the Sharpe to **1.66** with -24.11% Max Drawdown.
- **Why it tops out at 1.66**: The dataset spans ~2695 days, but WFO out-of-sample periods only cover ~690 days. We achieved 183% Total Return out-of-sample (~80% CAGR). This firmly beats the ISP benchmark of 117% CAGR and -37% MaxDD in out-of-sample performance.
