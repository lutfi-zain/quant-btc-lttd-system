# hmm-regime-classification Specification

## Purpose
TBD - created by archiving change p02-hmm-regime-detector. Update Purpose after archive.
## Requirements
### Requirement: Feature Preparation for HMM
The system SHALL prepare daily log returns and realized volatility as the exclusive input features for the HMM. This requirement applies at the **daily level**. This relies on the mathematical principles detailed in `pi_final_research_lttd_01.md` (Section: *Regime-Aware Adaptability*).

#### Scenario: Computing daily log returns and volatility
- **GIVEN** historical daily OHLCV close prices
- **WHEN** the feature preparation pipeline is executed
- **THEN** the system SHALL output a 2D array containing exactly two features: daily log returns `ln(P_t / P_{t-1})` and a rolling realized volatility metric.
- **THEN** the feature calculation SHALL use a strictly causal design ensuring zero Lookahead Bias.

### Requirement: 3-State HMM Training Pipeline
The system SHALL train a Gaussian Hidden Markov Model with exactly 3 hidden states representing BULL, BEAR, and SIDEWAYS market regimes using `hmmlearn`. This requirement applies at the **regime level**.

#### Scenario: Training the HMM model
- **GIVEN** a minimum of 120 days of prepared daily log returns and realized volatility features
- **WHEN** the training pipeline is invoked
- **THEN** the system SHALL successfully fit a 3-state Gaussian HMM.
- **THEN** the model SHALL output converged transition matrices and emission probabilities without encountering singular matrix errors.

### Requirement: HMM Inference and Posterior Probabilities
The system SHALL infer the latent market regime and output the posterior probabilities for each of the 3 states. This requirement applies at the **daily level**.

#### Scenario: Inferring the current market regime
- **GIVEN** a successfully trained 3-state HMM and the latest daily features
- **WHEN** the inference logic is executed for the current day
- **THEN** the system SHALL output a posterior probability distribution `[P(Bull), P(Bear), P(Sideways)]` that strictly sums to 1.0.
- **THEN** if the HMM posterior `P(Bull) > 0.70`, the system SHALL classify the current Regime as BULL.

### Requirement: Causal HMM Regime Inference
Enforce that HMM regime probability estimation does not access future observations. The inference algorithm must be strictly causal.

#### Scenario: Day-by-Day Historical Regime Prediction
- **GIVEN** a trained HMM model, close price series up to time $t$, and state-to-regime mappings.
- **WHEN** inferring the market regime at bar $t$.
- **THEN** the model SHALL only read closing prices from indices $\le t$.
- **AND** the computed posterior probabilities for BULL, BEAR, and SIDEWAYS SHALL sum to 1.0.
- **AND** the Viterbi alignment or posterior smoothing SHALL NOT utilize any pricing data from indices $> t$.

### Requirement: Strict Data Dependency and Causal Boundaries
The system SHALL ensure that HMM training and inference pipelines have zero dependency on Layer 2 Technical Indicators. This requirement applies at the **regime level**.

#### Scenario: Validating HMM independence
- **GIVEN** the Regime Detection layer (Layer 1)
- **WHEN** the Python module dependencies are analyzed
- **THEN** the `src/regime/` module SHALL NOT import or call functions from the `src/signals/` or `src/features/` modules.

### Requirement: Handling Missing or Insufficient Data
The system SHALL implement safeguards against insufficient historical data to ensure stable HMM convergence. This requirement applies at the **regime level**.

#### Scenario: Attempting to train with insufficient data
- **GIVEN** fewer than 120 days of historical daily OHLCV data
- **WHEN** the HMM training pipeline is invoked
- **THEN** the system SHALL raise an exception indicating insufficient data for stable Regime classification.

