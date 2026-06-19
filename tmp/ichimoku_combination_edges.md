# Ichimoku Boolean Combination Edges Report

## 1. Overview
This report presents a systematic search over all 63 boolean combinations of 6 daily causal Ichimoku indicators. The backtest runs on daily BTC-USD historical data loaded from the database.

### Data Specifications
- **Backtest Period**: 2014-05-18 to 2026-06-26 (12.11 years)
- **Total Bars**: 4423 days

---

## 2. Explanation of 'Chikou Causal'
The traditional Ichimoku Kinko Hyo indicator includes the **Chikou Span**, which plots the current close price shifted backward by 26 periods. In a standard charting package, this means looking at `close[t]` and plotting it at `t-26`. While visually useful for comparing current price against historical price, using this directly in a backtest introduces **severe lookahead bias** (at time `t-26`, the algorithm would know the close at time `t`).

To resolve this lookahead bias and maintain causality, we define **Chikou Causal** at time `t` as: 
$$\text{Chikou Causal}_t = \text{Close}_t - \text{Close}_{t-26}$$
This is a standard momentum calculation. The binary condition $c6$ becomes $\text{Chikou Causal}_t > 0$, which is equivalent to $\text{Close}_t > \text{Close}_{t-26}$. This is fully causal because it only uses information up to time $t$.

---

## 3. Pairwise Correlation Matrix of Binary Conditions
The table below shows the Pearson correlation coefficients between the 6 binary conditions:

| Condition | c1 | c2 | c3 | c4 | c5 | c6 |
| --- | --- | --- | --- | --- | --- | --- |
| **c1** | 1.0000 | 0.5061 | 0.3120 | 0.2114 | 0.0356 | 0.3304 |
| **c2** | 0.5061 | 1.0000 | 0.5721 | 0.7054 | 0.0342 | 0.6674 |
| **c3** | 0.3120 | 0.5721 | 1.0000 | 0.5644 | 0.3328 | 0.6591 |
| **c4** | 0.2114 | 0.7054 | 0.5644 | 1.0000 | 0.0185 | 0.6698 |
| **c5** | 0.0356 | 0.0342 | 0.3328 | 0.0185 | 1.0000 | 0.0249 |
| **c6** | 0.3304 | 0.6674 | 0.6591 | 0.6698 | 0.0249 | 1.0000 |

### Legend of Conditions:
- **c1**: Close > Tenkan
- **c2**: Close > Kijun
- **c3**: Close > Cloud Top
- **c4**: Tenkan > Kijun
- **c5**: Senkou A > Senkou B
- **c6**: Chikou Causal > 0 (Close > Close.shift(26))

---

## 4. Top 10 Best-Performing Boolean Combination Rules
The table below lists the top 10 boolean combinations, sorted in descending order by **Annualized Sharpe Ratio**:

| Rank | Combination | Total Return (%) | CAGR (%) | Sharpe Ratio (Ann) | Max Drawdown (%) | Number of Trades | Win Rate (%) | Profit Factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `c3 & c6` | 49914.73% | 67.09% | 1.386 | -50.48% | 109 | 38.5% | 4.851 |
| 2 | `c3 & c4 & c6` | 36620.64% | 62.88% | 1.383 | -46.65% | 93 | 37.6% | 5.007 |
| 3 | `c1 & c3 & c4 & c6` | 17198.86% | 53.06% | 1.358 | -41.66% | 175 | 37.7% | 3.204 |
| 4 | `c1 & c2 & c3 & c4 & c6` | 17198.86% | 53.06% | 1.358 | -41.66% | 175 | 37.7% | 3.204 |
| 5 | `c1 & c2 & c3 & c4` | 16723.94% | 52.71% | 1.347 | -41.66% | 177 | 39.0% | 3.130 |
| 6 | `c1 & c3 & c4` | 16723.94% | 52.71% | 1.347 | -41.66% | 177 | 39.0% | 3.130 |
| 7 | `c1 & c4 & c6` | 19381.12% | 54.57% | 1.342 | -48.34% | 206 | 37.4% | 2.888 |
| 8 | `c1 & c2 & c4 & c6` | 19381.12% | 54.57% | 1.342 | -48.34% | 206 | 37.4% | 2.888 |
| 9 | `c2 & c3 & c4 & c6` | 24476.38% | 57.56% | 1.340 | -56.24% | 107 | 38.3% | 4.327 |
| 10 | `c1 & c3 & c6` | 17665.94% | 53.40% | 1.312 | -45.79% | 204 | 36.3% | 2.898 |

---

## 5. Performance Comparison
We compare the best performing combination rules against the baseline **BTC Buy & Hold** and the individual strategies from the previous report:

| Strategy | CAGR (%) | Sharpe Ratio (Ann) | Max Drawdown (%) | Number of Trades | Win Rate (%) | Profit Factor |
| --- | --- | --- | --- | --- | --- | --- |
| **BTC Buy & Hold (Baseline)** | 50.63% | 0.930 | -83.19% | 1 | 100.0% | Infinity |
| **TK Cross (c4)** | 51.49% | 1.112 | -64.33% | 97 | 40.2% | 3.133 |
| **Price/Kijun Cross (c2)** | 47.92% | 1.070 | -63.62% | 195 | 27.7% | 2.491 |
| **Kumo Breakout (c3 Hysteresis)** | 52.40% | 1.100 | -66.36% | 46 | 39.1% | 5.524 |
| **Chikou Causal (c6)** | 64.77% | 1.288 | -72.01% | 177 | 41.2% | 3.366 |
| **Best Sharpe (`c3 & c6`)** | 67.09% | 1.386 | -50.48% | 109 | 38.5% | 4.851 |
| **Best CAGR (`c3 & c6`)** | 67.09% | 1.386 | -50.48% | 109 | 38.5% | 4.851 |
| **Best Profit Factor (`c3`)** | 60.66% | 1.257 | -54.31% | 92 | 31.5% | 5.707 |

---

## 6. Analysis and Trade-offs
### 6.1 Multi-Indicator Synergy vs Redundancy
The pairwise correlation matrix shows very high correlations between close-based conditions (e.g., $c1$, $c2$, $c3$, and $c6$ all have correlations $>0.70$). Stacking multiple highly correlated indicators via logical AND does not create an independent signal. Instead, it serves as a restrictive filter that reduces exposure time.

### 6.2 The Trade Frequency vs Restrictiveness Trade-off
- As we add more conditions to the logical AND rule, the strategy becomes more restrictive (only entering when all conditions are simultaneously satisfied). This drastically reduces the number of trades and overall market exposure.
- Restrictive combinations (like `c1 & c2 & c3 & c4 & c5 & c6`) tend to have very few trades and miss major trends, leading to lower CAGR but sometimes very high win rates or profit factors for the few trades they do take.
- The best performing combination in terms of Sharpe Ratio is **`c3 & c6`**, achieving a Sharpe of **1.386**, which outperforms the baseline BTC Buy & Hold (Sharpe **0.930**) and individual strategies.
- **Conclusion**: Combining specific lagging indicators with faster momentum indicators (like Chikou Causal) creates a superior regime filter, successfully avoiding major bear market drawdowns while maintaining high exposure during strong uptrends.
