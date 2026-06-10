## ADDED Requirements

### Requirement: Causal Relative Strength Index (RSI) Indicator
The RSI indicator MUST strictly inherit from the `CausalFilter` base class to prevent Lookahead Bias, ensuring it only reads `source[i]` for i≥0. It measures momentum by comparing the magnitude of recent gains to recent losses. The continuous RSI value (0 to 100) MUST be mapped to a discrete Indicator Score ∈ {-1, +1}. This requirement applies at the **daily level**. *(Reference: `pi_final_research_lttd_01.md` - Indicator Audit Decisions)*

#### Scenario: RSI crossing centerline
- **GIVEN** a daily OHLCV price series $P_t$, and a `CausalFilter` RSI implementation using pandas `series.ewm(span=N, adjust=False).mean()` to strictly ensure $y_t = f(P_{t}, P_{t-1}, \dots, P_{0})$ without `shift(-1)` Lookahead Bias
- **WHEN** the causal RSI continuous value is calculated at day `t`
- **THEN** the output MUST be a discrete Indicator Score ∈ {-1, +1}
- **AND** the Indicator Score MUST be exactly `+1` if the continuous RSI value is > 50
- **AND** the Indicator Score MUST be exactly `-1` if the continuous RSI value is <= 50

### Requirement: Causal Moving Average Convergence Divergence (MACD) Indicator
The MACD indicator MUST be implemented as a causal filter, avoiding any centered or symmetric windows. It calculates the difference between a short-term and a long-term Exponential Moving Average (EMA). The MACD histogram (MACD line minus Signal line) MUST be mapped to a discrete Indicator Score ∈ {-1, +1}. This requirement applies at the **daily level**. *(Reference: `pi_final_research_lttd_01.md` - Mathematical Proofs for Causal Filtering)*

#### Scenario: MACD zero-line crossover
- **GIVEN** a daily OHLCV price series $P_t$, and a `CausalFilter` MACD implementation computing $EMA_{short}(P_t) - EMA_{long}(P_t)$ using numpy/pandas exponential weighted functions that depend exclusively on past states
- **WHEN** the MACD histogram is evaluated at day `t`
- **THEN** the output MUST be a discrete Indicator Score ∈ {-1, +1}
- **AND** the Indicator Score MUST be exactly `+1` if the MACD histogram > 0
- **AND** the Indicator Score MUST be exactly `-1` if the MACD histogram <= 0

### Requirement: Causal True Strength Index (TSI) Indicator
The TSI indicator MUST strictly adhere to the `CausalFilter` constraint. It measures trend conviction by double-smoothing price momentum using EMAs. The continuous TSI value MUST be mapped to a discrete Indicator Score ∈ {-1, +1} based on its zero crossover. This requirement applies at the **daily level**. *(Reference: `pi_final_research_lttd_01.md` - Layer Design for Layer 2: Signal Engine)*

#### Scenario: TSI momentum conviction
- **GIVEN** a daily OHLCV price series $P_t$, computing the momentum $M_t = P_t - P_{t-1}$, and applying double EMA smoothing $EMA_{s2}(EMA_{s1}(M_t))$ via pandas causality-preserving transformations
- **WHEN** the continuous TSI value is computed at day `t` strictly without Lookahead Bias
- **THEN** the output MUST be a discrete Indicator Score ∈ {-1, +1}
- **AND** the Indicator Score MUST be exactly `+1` if the TSI value > 0
- **AND** the Indicator Score MUST be exactly `-1` if the TSI value <= 0

## Non-Goals
- We will not implement non-causal smoothing methods (e.g., Savitzky-Golay with symmetric windows) as they introduce Lookahead Bias.
- We will not aggregate these Indicator Scores into a Final Score; that belongs to Layer 4 (Ensemble Aggregation).
- We will not run Variance Inflation Factor (VIF) pruning in this batch; VIF > 10 checks belong to Layer 3 (Feature Processing).
