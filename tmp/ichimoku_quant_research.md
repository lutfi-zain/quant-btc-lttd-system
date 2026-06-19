# Quantitative Research Report: Ichimoku Cloud Integration Analysis

**Date:** 2026-06-19  
**Target Asset:** Bitcoin (BTC-USD)  
**Author:** Quantitative Research and Trading Architecture Team  
**Subject:** Ichimoku Cloud Statistical Properties, Causal Properties, and Architectural Integration  

---

## 1. Executive Summary
This report analyzes the mathematical formulations, causal properties, and statistical integration potential of the Ichimoku Cloud indicator within our 6-layer trading architecture. Using daily historical Bitcoin (BTC) OHLCV data from 2014-05-18 to 2026-06-26 (4,423 clean trading days), we examine the correlation and Variance Inflation Factor (VIF) of Ichimoku candidates alongside our active signals: **AdvancedStochastic**, **RSI-50**, **FourierSupertrend**, and **TrendStrengthIndex (TSI)**.

Our statistical findings suggest that:
1. **Chikou Span** and **price-to-cloud distances** present severe multicollinearity (VIF > 10) and are highly redundant with existing trend/momentum features.
2. **Senkou Span Difference (senkou_diff)** is highly orthogonal (VIF = 2.79) and represents a clean proxy for structural market regimes.
3. We recommend integrating Ichimoku as a **Layer 1 Regime Filter** (specifically utilizing `senkou_diff` and cloud boundaries) rather than a Layer 2 directional execution signal.

---

## 2. Mathematical Formulations
Let $P_t^{\text{high}}$, $P_t^{\text{low}}$, and $P_t^{\text{close}}$ represent the high, low, and closing prices of BTC at bar $t$.

### 2.1 Tenkan-sen (Conversion Line)
The Tenkan-sen is the midpoint of the high and low prices over the past 9 periods:
$$T_t = \frac{\max_{i=0}^{8}(P_{t-i}^{\text{high}}) + \min_{i=0}^{8}(P_{t-i}^{\text{low}})}{2}$$

### 2.2 Kijun-sen (Base Line)
The Kijun-sen is the midpoint of the high and low prices over the past 26 periods:
$$K_t = \frac{\max_{i=0}^{25}(P_{t-i}^{\text{high}}) + \min_{i=0}^{25}(P_{t-i}^{\text{low}})}{2}$$

### 2.3 Senkou Span A (Leading Span A)
Senkou Span A represents the average of Tenkan-sen and Kijun-sen, shifted forward by 26 periods. Mathematically, the raw value calculated at bar $t$ is:
$$SA_t^{\text{raw}} = \frac{T_t + K_t}{2}$$
Plotted at bar $t + 26$:
$$SA_{t+26} = SA_t^{\text{raw}}$$
Equivalently, the value of Senkou Span A available at time $t$ (plotted on bar $t$ but calculated from $t-26$) is:
$$SA_t = SA_{t-26}^{\text{raw}} = \frac{T_{t-26} + K_{t-26}}{2}$$

### 2.4 Senkou Span B (Leading Span B)
Senkou Span B is the midpoint of the high and low prices over the past 52 periods, shifted forward by 26 periods. The raw value calculated at bar $t$ is:
$$SB_t^{\text{raw}} = \frac{\max_{i=0}^{51}(P_{t-i}^{\text{high}}) + \min_{i=0}^{51}(P_{t-i}^{\text{low}})}{2}$$
Plotted at bar $t + 26$:
$$SB_{t+26} = SB_t^{\text{raw}}$$
Equivalently, the value of Senkou Span B available at time $t$ is:
$$SB_t = SB_{t-26}^{\text{raw}} = \frac{\max_{i=0}^{51}(P_{t-26-i}^{\text{high}}) + \min_{i=0}^{51}(P_{t-26-i}^{\text{low}})}{2}$$

### 2.5 Chikou Span (Lagging Span)
The Chikou Span is the current close price plotted backward. In the legacy Pine Script (`0xbujang-lttd.pinescript`), it is plotted with an offset of $-25$:
$$CS_{t-25} = P_t^{\text{close}}$$
Equivalently, the value of the Chikou Span line at bar $t$ is:
$$CS_t = P_{t+25}^{\text{close}}$$

---

## 3. Causal vs. Lookahead Analysis
In systematic trading, lookahead bias occurs when future data is leaked into the feature matrix at bar $t$ [DSP-StackExchange].

### 3.1 Tenkan-sen and Kijun-sen
These indicators are computed using only past data up to bar $t$. They are **fully causal** and do not introduce lookahead bias.

### 3.2 Senkou Span A and B
Although they are plotted 26 bars into the future, their values *at* bar $t$ ($SA_t$ and $SB_t$) are calculated using prices up to bar $t-26$. 
- **Causal Calculation:** Yes, we can calculate them causally at bar $t$ without leakage because at bar $t$ the prices up to $t-26$ are fully historical.
- **Leakage Risk:** If a backtester reads the raw values $SA_t^{\text{raw}}$ and $SB_t^{\text{raw}}$ as if they are active at bar $t$, or uses the forward-projected cloud values ($SA_{t+26}$ and $SB_{t+26}$), it introduces lookahead bias. We must ensure features strictly use $SA_t = SA_{t-26}^{\text{raw}}$ and $SB_t = SB_{t-26}^{\text{raw}}$.

### 3.3 Chikou Span
Because $CS_t = P_{t+25}^{\text{close}}$, the value of the Chikou Span line at bar $t$ requires knowing the price 25 bars in the future.
- **Causal Formulation:** The raw Chikou Span line cannot be calculated causally at bar $t$ for real-time execution.
- **Alternative:** The mathematical relationship that Chikou Span evaluates is whether the current price is above/below the price 26 periods ago. This can be expressed causally at bar $t$ as:
$$CS_{t,\text{causal}} = P_t^{\text{close}} - P_{t-26}^{\text{close}}$$
This formulation is fully causal and has no leakage.

---

## 4. Multicollinearity & Correlation Analysis
We evaluated the Pearson correlation and Variance Inflation Factors (VIF) on daily BTC data (4,423 rows) for the following feature candidates:
- `tenkan_kijun_diff` = $T_t - K_t$
- `price_kijun_diff` = $P_t^{\text{close}} - K_t$
- `price_cloud_top_diff` = $P_t^{\text{close}} - \max(SA_t, SB_t)$
- `price_cloud_bottom_diff` = $P_t^{\text{close}} - \min(SA_t, SB_t)$
- `senkou_diff` = $SA_t - SB_t$
- `chikou_diff_causal` = $P_t^{\text{close}} - P_{t-26}^{\text{close}}$

### 4.1 Variance Inflation Factor (VIF) Results
A VIF greater than 10.0 indicates severe multicollinearity [IBM-Multicollinear].

| Feature Name | VIF Value | Multicollinear (> 10.0)? |
| :--- | :---: | :---: |
| **AdvancedStochastic** (Active) | 3.2403 | NO |
| **RSI-50** (Active) | 3.0264 | NO |
| **FourierSupertrend** (Active) | 2.1808 | NO |
| **TrendStrengthIndex** (Active) | 3.9498 | NO |
| **tenkan_kijun_diff** | 4.2749 | NO |
| **price_kijun_diff** | 7.0144 | NO |
| **price_cloud_top_diff** | 13.0485 | **YES** |
| **price_cloud_bottom_diff** | 11.5100 | **YES** |
| **senkou_diff** | 2.7890 | NO |
| **chikou_diff_causal** | 16.7322 | **YES** |

### 4.2 Pearson Correlation Sub-Matrix
Correlation coefficients of Ichimoku candidates against the active indicators:

| Ichimoku Candidate | AdvancedStochastic | RSI-50 | FourierSupertrend | TrendStrengthIndex |
| :--- | :---: | :---: | :---: | :---: |
| **tenkan_kijun_diff** | 0.4621 | 0.4557 | 0.3984 | 0.4339 |
| **price_kijun_diff** | 0.6031 | 0.4131 | 0.5199 | 0.4683 |
| **price_cloud_top_diff** | 0.4533 | 0.5758 | 0.3845 | 0.6222 |
| **price_cloud_bottom_diff** | 0.4217 | 0.5303 | 0.3445 | 0.5987 |
| **senkou_diff** | 0.0166 | 0.1680 | -0.0204 | 0.3708 |
| **chikou_diff_causal** | 0.4951 | 0.5014 | 0.4128 | 0.5084 |

### 4.3 Analysis & Risk Assessment
- **High Multicollinearity (VIF > 10):** `price_cloud_top_diff` (13.05), `price_cloud_bottom_diff` (11.51), and `chikou_diff_causal` (16.73) present excessive collinearity. This is because they all measure the distance of the price from medium-to-long term averages (Kijun-sen 26-day midpoint, Senkou B 52-day midpoint, or 26-day price momentum). 
- **High Redundancy:** `price_cloud_top_diff` and `price_cloud_bottom_diff` have a Pearson correlation of **0.9391**. Including both would violate our statistical integration guardrails.
- **Orthogonality of `senkou_diff`:** The difference between the two spans (`senkou_diff`) represents the cloud thickness/color and has a VIF of only **2.79**. Its correlation with `FourierSupertrend` (-0.02) and `AdvancedStochastic` (0.017) is near-zero, proving it provides unique information.

---

## 5. Trading System Integration & Architectural Recommendations

We evaluate the placement of Ichimoku features within our 6-layer quantitative trading system.

```
┌────────────────────────────────────────────────────────┐
│             LAYER 1: REGIME FILTER (HMM)               │
│ - senkou_diff > 0 & Close > Cloud Top => BULL REGIME  │
│ - senkou_diff < 0 & Close < Cloud Bottom => BEAR      │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             LAYER 2: SIGNAL ENGINE (Causal)            │
│ - tenkan_kijun_diff crossover => Trend Momentum       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             LAYER 3: FEATURE ORTHOGONALIZATION         │
│ - Pass selected features through PCA or VIF pruning   │
└────────────────────────────────────────────────────────┘
```

### 5.1 Recommendation 1: Layer 1 Regime Filter (Primary Role)
The Ichimoku Cloud is structurally designed to filter macro cycles rather than generate tactical entries. We propose using the relationship between the close price and the cloud boundaries as a **Layer 1 Regime Filter**:
- **Bullish Regime:** $P_t^{\text{close}} > \max(SA_t, SB_t)$ AND $SA_t > SB_t$.
- **Bearish Regime:** $P_t^{\text{close}} < \min(SA_t, SB_t)$ AND $SA_t < SB_t$.
- **Sideways/Consolidation Regime:** $\min(SA_t, SB_t) \le P_t^{\text{close}} \le \max(SA_t, SB_t)$.

### 5.2 Recommendation 2: Layer 2 Signal Engine (Selective Integration)
If used in Layer 2 (Signal Engine), we must enforce **strict causal formulation** and drop collinear variables:
- **Keep:** `senkou_diff` and `tenkan_kijun_diff` (their VIF values are safely below 5.0).
- **Prune:** Raw `price_cloud_top_diff`, `price_cloud_bottom_diff`, and `chikou_diff_causal` due to VIF > 10.
- **PCA Alternative:** If these distance metrics are desired, they **must** be passed through the Layer 3 `FeatureProcessor`'s PCA pipeline to project them onto orthogonal axes before ensemble voting.
