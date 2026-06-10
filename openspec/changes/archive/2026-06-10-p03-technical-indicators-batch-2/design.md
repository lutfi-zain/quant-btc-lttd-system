## Context

Standard trend indicators in the quantitative LTTD (Long-Term Trend Direction) pipeline suffer from fixed lookback periods, causing lag during regime shifts and whipsaws during sideways consolidation. Based on the system's quantitative blueprint, Bitcoin's mean-reversion half-life has structurally expanded (now 300+ days). Fixed-length Moving Averages or static Supertrend variants are ill-equipped to handle this dynamic nature. 

To resolve this, we are introducing the **Adaptive Fourier Transform Supertrend** (Indicator 5 from the research blueprint) to the Layer 2 Signal Engine. This indicator operates in the frequency domain, extracting the dominant cyclical frequency of the asset to dynamically tune the Supertrend's parameters, yielding a highly reactive, causal trend filter with low cross-correlation (low VIF) to existing momentum and volatility metrics.

## Goals / Non-Goals

**Goals:**
- Implement the Adaptive Fourier Transform Supertrend as a causal signal generator in `src/signals/`.
- Ensure the indicator dynamically tunes its period based on the dominant frequency of recent price action using Discrete Fourier Transform (DFT).
- Enforce strict causality (no lookahead bias) by deriving the signal purely from past data and inheriting from the `CausalFilter` base class.
- Standardize the output to a binary `Indicator Score` ∈ {-1, +1}.

**Non-Goals:**
- Applying the Fourier transform to Layer 1 (Regime Detection) or Layer 4 (Ensemble Aggregation). This change is strictly isolated to Layer 2.
- Modifying the underlying data fetching logic or introducing new on-chain dependencies.

## Decisions

### 1. Extractor of Dominant Cycle: Sliding Window Fast Fourier Transform (FFT)
**Decision:** Use `scipy.fft` on a rolling window to extract the dominant spectral period (highest amplitude frequency bin).
**Rationale:** The FFT transforms time-series data (e.g., log returns or price changes) into the frequency domain. By applying FFT over a rolling causal window (e.g., $N=256$ days), we can dynamically calculate the dominant period $T_{dom}$. The Supertrend length parameter is then mapped proportionally to $T_{dom}$.
**Alternatives Considered:** 
- *Goertzel Algorithm or Sliding DFT:* While $O(1)$ per step, Bitcoin's daily sampling frequency implies rolling windows of $\sim 256$ data points. Executing a standard $O(N \log N)$ FFT on an array of 256 elements per day is computationally trivial in Python and simplifies the implementation over maintaining complex sliding phase states.

### 2. Causality and Window Alignment
**Decision:** The rolling FFT window at time $t$ will strictly use the slice $[t - N, t-1]$.
**Rationale:** Centered windows or asymmetric smoothing filters (like the flawed Pine Script Savitzky-Golay filter) introduce fatal lookahead bias, invalidating backtests. The Adaptive Fourier Supertrend must inherit from `CausalFilter`. The signal at time $t$ will solely rely on closed bars up to time $t-1$ (shift(1) equivalent in pandas).
**Alternatives Considered:**
- *Zero-lag padding or predictive boundary handling:* Rejected as these often inadvertently leak future data during cross-validation. Pure causal truncation is mathematically sound and safe.

### 3. Supertrend Parameter Mapping
**Decision:** Dynamically update the ATR lookback period using the extracted dominant frequency.
**Rationale:** The traditional Supertrend relies on a static Average True Range (ATR) period and a static multiplier. We will map the dominant cycle length $T_{dom}$ to the ATR period dynamically (e.g., $ATR\_Period = \max(\min\_period, \lfloor T_{dom} / 2 \rfloor)$). This allows the Supertrend's volatility bands to expand and contract not just with magnitude, but with the structural frequency of the trend.

### 4. Binary Score Standardization
**Decision:** Output +1 if the closing price is strictly greater than the Supertrend upper band, and -1 if below.
**Rationale:** Layer 3 (Feature Processing) and Layer 4 (Ensemble Aggregation) expect normalized dimensional inputs for PCA orthogonalization. Continuous scores or raw price bands would distort the variance inflation analysis.

## Risks / Trade-offs

- **[Risk] High-Frequency Noise in FFT:** Small amplitude peaks at high frequencies could cause the dominant period $T_{dom}$ to jitter wildly between bars, destabilizing the Supertrend parameters.
  - **Mitigation:** Apply a low-pass causal filter (like a short EMA) to the raw prices *before* performing the FFT, or use a median filter over the extracted dominant frequencies (e.g., rolling 5-day median of $T_{dom}$) to smooth the period transitions.
- **[Risk] Lookahead Bias via Improper Implementation:** Accidental symmetric filtering or using `pandas.Series.rolling(center=True)`.
  - **Mitigation:** Mandate a `test_no_lookahead()` unit test specifically for the Adaptive Fourier Supertrend. The test will assert that the value computed at index $t$ remains identical whether the underlying array length is $t$ or $t+100$.

## Migration Plan

1. Create the `AdaptiveFourierSupertrend` class in `src/signals/fourier_supertrend.py`.
2. Ensure inheritance from `CausalFilter`.
3. Add tests in `tests/signals/test_fourier_supertrend.py`, specifically checking against lookahead bias.
4. Integrate the new indicator into the primary signal pipeline (accessible to Layer 3 feature processing).
5. Run the system-wide VIF (Variance Inflation Factor) checks to ensure orthogonal contribution (VIF < 10) compared to existing Kalman RSI and volatility metrics.

## Open Questions

- What is the optimal rolling window size $N$ for the FFT? (To be resolved via Layer 4 WFO or set to 256/365 to cover the structural half-life).
- Should the multiplier parameter of the Supertrend be dynamically scaled alongside the ATR period, or kept static? (Will default to static `multiplier=3.0` and observe performance).
