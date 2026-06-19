# Ichimoku Boolean Edges Report

## Understanding Chikou Causal and Lookahead Bias

The **Chikou Span** (Lagging Span) is a core component of the Ichimoku Kinko Hyo indicator system. Traditionally, it is calculated as the current period's closing price plotted 26 periods *backwards* (into the past) on the chart. 

While this is an excellent visual tool for human traders—allowing them to quickly see if the current price is higher or lower than the price 26 days ago by simply looking at the past—it introduces a critical danger in algorithmic trading: **Lookahead Bias**.

### The Danger of the Legacy Chikou Span
If a backtesting script naively queries the condition `Chikou > Price` at historical bar `t`, it often accidentally looks up the closing price of `t + 26`. This means the algorithm is making decisions today using data from 26 days in the future, artificially inflating backtest performance and leading to catastrophic failures in live trading.

### The "Chikou Causal" Solution
To resolve this lookahead bias and make the signal strictly **causal** (relying only on past and present data), we invert the temporal relationship in Python:
- We define **Chikou Causal (C)** as the closing price from exactly 26 periods ago: `C = close.shift(26)`.
- We then use the logical condition: `Price (P) > C`.

This strictly causal comparison (`P > C`) accurately answers the original intent of the Chikou Span: *"Is today's price higher than the price 26 days ago?"* without leaking any future data into the model.

---

## Top 10 Ichimoku Boolean Edge Combinations

We tested all single Ichimoku boolean rules and combinations of two rules on the Bitcoin daily dataset (`database/lttd.db`) and ranked them by their Sharpe ratio. The strategy assumes a 1/0 long-only signal with daily log returns shifted by 1 day to prevent lookahead.

Here are the top 10 best-performing rule combinations:

| Rank | Rule Combination | Sharpe Ratio | CAGR | Time in Market (Trades_pct) |
|------|------------------|--------------|------|-----------------------------|
| 1 | `P > SB` AND `P > C` | 1.180764 | 67.43% | 44.30% |
| 2 | `P > T` AND `P > SA` | 1.128909 | 57.06% | 38.67% |
| 3 | `P > T` AND `T > K` | 1.116983 | 53.30% | 34.71% |
| 4 | `P > T` AND `P > C` | 1.109224 | 55.02% | 38.78% |
| 5 | `P > SA` AND `P > C` | 1.093505 | 63.94% | 49.10% |
| 6 | `P > C` AND `T > K` | 1.070567 | 59.40% | 46.29% |
| 7 | `P > C` | 1.063045 | 64.71% | 55.54% |
| 8 | `P > SA` AND `P > SB` | 1.043951 | 61.11% | 49.19% |
| 9 | `P > K` AND `P > SA` | 1.032022 | 55.49% | 44.98% |
| 10 | `P > SA` AND `T > K` | 1.030443 | 56.59% | 44.73% |

*Legend:*
* `P` = Current Price (Close)
* `T` = Tenkan-sen (9-period)
* `K` = Kijun-sen (26-period)
* `SA` = Senkou Span A (shifted forward 26 periods)
* `SB` = Senkou Span B (shifted forward 26 periods)
* `C` = Chikou Causal (Price 26 periods ago)
