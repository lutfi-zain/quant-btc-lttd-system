## Non-Goals
- DO NOT implement any regime detection logic (handled in Layer 1).
- DO NOT implement indicator aggregation or voting (handled in Layer 4).
- DO NOT use any centered moving averages, Savitzky-Golay symmetric filters, or Pine Script `calc_on_every_tick` equivalents.
- DO NOT fetch or process on-chain data (handled by `brk-client` in separate signals).

## ADDED Requirements

### Requirement: Causal Filter Base Class
The `CausalFilter` base class must be implemented in Layer 2 (`src/signals/`) to enforce strict causality. All Technical Indicators must inherit from this class. It guarantees that any calculation at time index `t` only uses data points up to `t`. This applies at the **bar level**. Reference the architectural blueprint `pi_final_research_lttd_01.md` for causality constraints.

#### Scenario: Enforcing No Lookahead Bias
- **GIVEN** a time series of OHLCV daily data up to time `t+N`
- **WHEN** the `CausalFilter` subclass computes the Indicator Score at time `t`
- **THEN** the computed output MUST exactly match the output computed if the series was truncated at time `t`
- **THEN** an automated `test_no_lookahead()` MUST pass by verifying zero variance when future bars are appended

### Requirement: Kalman Filtered RSI Indicator
A Technical Indicator applying a 1D Kalman Filter to the Relative Strength Index (RSI) to estimate hidden momentum states with zero lookahead bias. This applies at the **daily level**. Output must be an Indicator Score ∈ {-1, +1}.

#### Scenario: Valid Momentum Indicator Score Generation
- **GIVEN** an array of daily OHLCV data
- **WHEN** the `KalmanRSI` indicator processes the data through its causal filter at time `t`
- **THEN** it MUST return an Indicator Score of `+1` for bullish momentum or `-1` for bearish momentum
- **THEN** the computation MUST ONLY use historical prices without lookahead bias

### Requirement: Adaptive Fourier Transform Supertrend Indicator
A Technical Indicator that applies an adaptive fast Fourier transform (FFT) over a rolling causal window to extract dominant cycle frequencies and computes a Supertrend-like metric for spectral trend classification. This applies at the **daily level**. Output must be an Indicator Score ∈ {-1, +1}.

#### Scenario: Spectral Frequency Dominance Shift
- **GIVEN** a causal window of historical daily closing prices
- **WHEN** the `FourierSupertrend` detects a structural shift in the dominant frequency component signaling a bullish trend
- **THEN** the indicator MUST output an Indicator Score of `+1`
- **THEN** the filter must strictly only observe historical prices (`source[i]` for `i >= 0` past lag)

### Requirement: Trend Strength Index (Volatility Distance)
A Technical Indicator computing the distance between a Volume Weighted Moving Average (VWMA) and price, normalized by the Average True Range (ATR). This applies at the **daily level**. Captures trend conviction without multicollinearity against pure momentum. Output must be an Indicator Score ∈ {-1, +1}.

#### Scenario: Strong Volatility-Adjusted Bullish Trend
- **GIVEN** daily OHLCV data with high volume expansion
- **WHEN** the VWMA crosses above price by a distance greater than a configured ATR threshold
- **THEN** the `TrendStrengthIndex` MUST output an Indicator Score of `+1`
- **THEN** the indicator MUST maintain a VIF < 10 when measured against `KalmanRSI` and `FourierSupertrend` over the WFO training window
