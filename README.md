<p align="center">
  <img src="https://img.shields.io/badge/BTC-LTTD-F7931A?style=for-the-badge&logo=bitcoin&logoColor=white" alt="BTC LTTD" />
</p>

<h1 align="center">quant-btc-lttd-system</h1>

<p align="center">
  <strong>Long-Term Trend Direction — Orthogonal Regime-Switching Ensemble for Bitcoin</strong>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white" alt="scikit-learn"></a>
  <a href="#"><img src="https://img.shields.io/badge/hmmlearn-HMM-4B8BBE" alt="hmmlearn"></a>
  <a href="#"><img src="https://img.shields.io/badge/brk--client-bitview.space-089981" alt="brk-client"></a>
  <a href="#"><img src="https://img.shields.io/badge/OpenSpec-spec--driven-6366F1" alt="OpenSpec"></a>
  <a href="#"><img src="https://img.shields.io/badge/Hono-API-E36002?logo=hono&logoColor=white" alt="Hono"></a>
  <a href="#"><img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React"></a>
  <a href="#"><img src="https://img.shields.io/badge/SQLite-WAL-07405e?logo=sqlite" alt="SQLite"></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Signal_Horizon-120–350_days-22c55e" alt="Horizon"></a>
  <a href="#"><img src="https://img.shields.io/badge/On--Chain_Source-bitview.space-089981" alt="On-chain"></a>
  <a href="#"><img src="https://img.shields.io/badge/Lookahead_Bias-zero_tolerance-ef4444" alt="Lookahead"></a>
  <a href="#"><img src="https://img.shields.io/badge/Aggregation-L1_Lasso_WFO-8b5cf6" alt="Aggregation"></a>
</p>

---

> **Classifies Bitcoin's macro directional bias — BULL / BEAR / SIDEWAYS — over a 120–350 day horizon.**  
> Built on quantitative, statistically-grounded principles: empirical OU half-life estimation, PCA orthogonalization, regime-switching HMM, and L1-regularized ensemble aggregation. No lookahead bias. No hardcoded signals. No information leakage.

<div align="center">

| Research Foundation | Value |
|---|---|
| **Signal Horizon** | 120 – 350 days (epoch-dependent, OU-derived) |
| **OU Mean-Reversion Half-Life** | ~300+ days (post-2020 institutional era) |
| **Technical Indicators** | 12 (PCA-orthogonalized → 3 principal components) |
| **On-Chain Metrics** | 4 (STH-MVRV, STH-NUPL, STH-SOPR, Supply in Profit) |
| **On-Chain Data Source** | [bitview.space](https://bitview.space) — free, no auth |
| **Regime Classes** | BULL · BEAR · SIDEWAYS (3-state Gaussian HMM) |
| **Aggregation Method** | L1-Lasso Logistic Regression + Walk-Forward Optimization |
| **Lookahead Bias** | Zero tolerance — every indicator uses `CausalFilter` |
| **Research Confidence** | 98% (exhaustive, 26 sources, 5 search rounds) |

</div>

---

## 📋 Table of Contents

- [Why LTTD?](#why-lttd)
- [Architecture Overview](#architecture-overview)
- [Signal Horizon — Quantitative Foundation](#signal-horizon--quantitative-foundation)
- [Regime Detection (Layer 1)](#layer-1-regime-detection)
- [Signal Engine (Layer 2)](#layer-2-signal-engine)
- [Feature Processing (Layer 3)](#layer-3-feature-processing)
- [Ensemble Aggregation (Layer 4)](#layer-4-ensemble-aggregation)
- [On-Chain Data — bitview.space BRK API](#on-chain-data--bitviewspace-brk-api)
- [Pine Script Audit (0xbujang-lttd)](#pine-script-audit)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Dashboard & API](#dashboard--api)
- [OpenSpec Workflow](#openspec-workflow)
- [Academic References](#academic-references)

---

## Why LTTD?

Most trading systems treat all time periods equally. Bitcoin does not.

BTC's price dynamics are governed by a **macro 4-year cycle** driven by halving-induced supply shocks, long-term holder accumulation/distribution, and institutional capital flows. A strategy that cannot separate a long macro bull from a post-cycle bear will whipsaw itself into capital destruction — regardless of how many indicators it uses.

**The LTTD system answers a single binary-ternary question:**

```
Is Bitcoin currently in a macro BULL, BEAR, or SIDEWAYS regime?
```

| Dimension | Typical System | LTTD System |
|---|---|---|
| **Signal horizon** | Fixed (e.g., 200-day MA) | Adaptive, OU-derived (120–350 days) |
| **Indicator correlation** | Ignored (stacked RSI variants) | Explicitly tested — VIF < 10 required |
| **On-chain data** | Hardcoded arrays or static thresholds | Live BRK API (`sth_mvrv`, `sth_nupl`, `sth_sopr_24h`) |
| **Regime awareness** | Single model for all markets | 3-state HMM — separate logic per regime |
| **Backtest validity** | Often lookahead-contaminated | CPCV + causal-only filters enforced |
| **Aggregation** | Simple average of scores | L1-Lasso logistic regression, WFO-trained |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                     │
│  (same persistence pattern as quant-btc-valuation-system)               │
│                                                                          │
│  bitview.space ──┐   (sth_mvrv, sth_nupl, sth_sopr_24h, sth_supply)    │
│  (BRK API)       │                                                      │
│  OHLCV Exchange ─┼──→ pandas DataFrame ──→ Feature Store               │
│  (daily BTC-USD) │         (confirmed bars only — barstate equiv.)       │
└──────────────────┴──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: REGIME DETECTION                             │
│                                                                          │
│  Input:  daily log returns + realized volatility                        │
│  Model:  3-state Gaussian HMM                                           │
│  Output: P(Bull), P(Bear), P(Sideways) posterior probabilities          │
│  Rule:   Layer 2–4 logic adapts based on active regime                  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LAYER 2: SIGNAL ENGINE                                │
│                                                                          │
│  12 Technical Indicators   →  Indicator Score ∈ {-1, +1}               │
│   (all CausalFilter-based, confirmed bars, no symmetric windows)        │
│                                                                          │
│  4 On-Chain Metrics        →  On-Chain Score ∈ {-1, +1}                │
│   (BRK API: sth_mvrv, sth_nupl, sth_sopr_24h, sth_supply_in_profit)    │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 LAYER 3: FEATURE PROCESSING                              │
│                                                                          │
│  Step 1: Z-score standardize all 16 indicator outputs                   │
│  Step 2: Covariance matrix → eigendecomposition                         │
│  Step 3: PCA → top 3 principal components (≥85% variance explained)    │
│  Step 4: VIF check — drop any indicator with VIF > 10 before PCA        │
│  Output: Orthogonal feature matrix, zero multicollinearity              │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 LAYER 4: ENSEMBLE AGGREGATION                            │
│                                                                          │
│  Model:  L1-Lasso Logistic Regression                                   │
│  Input:  PC₁, PC₂, PC₃ (orthogonal features from Layer 3)              │
│  Target: P(uptrend over N-day horizon) — Walk-Forward Optimization      │
│  WFO:    Train 3yr → Validate 6mo → Test 6mo → roll forward            │
│  Pruning: Lasso shrinks redundant β coefficients to exactly 0          │
│  Output: Final Score ∈ [-1.0, +1.0] + direction probability            │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 LAYER 5: EXECUTION ENGINE                                │
│                                                                          │
│  Regime-weighted position sizing:                                       │
│    P(Bull) × Final Score × Vol-target scalar → Position Size %         │
│  Zero position during SIDEWAYS regime (HMM posterior > 0.6)            │
│  Entry/Exit on confirmed daily bars only                                │
└──────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LAYER 6: PRESENTATION                                 │
│                                                                          │
│  SQLite (WAL) ──→ Hono v4 API (Bun) ──→ React SPA (Vite + TypeScript)  │
│                         │                     │                          │
│                   REST endpoints        Lightweight Charts               │
│                   (JSON responses)      Regime banner · Score gauge      │
│                                         On-chain panels · WFO grid      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Signal Horizon — Quantitative Foundation

A quant does not begin with indicators. A quant begins by measuring the **structural properties of the price series** to determine the appropriate signal period.

### Ornstein-Uhlenbeck Mean-Reversion Half-Life

Bitcoin's price deviation from its long-term equilibrium (Power Law trend) follows an Ornstein-Uhlenbeck (OU) process:

```
dx_t = θ(μ − x_t)dt + σ dW_t
```

The **half-life of mean reversion** — how long the system takes to revert halfway to equilibrium — is estimated empirically via discrete-time AR(1) regression:

```
Δx_t = α + β·x_{t-1} + ε_t    →    θ = -ln(1 + β)    →    λ = ln(2) / θ
```

**Empirical findings:**

```
  Era               Half-Life      Market Structure
  ─────────────     ──────────     ───────────────────────────────────
  Pre-2017          40–80 days     Retail-driven, high-frequency cycles
  Post-2020         300+ days      Institutional, macro-driven mega-cycles
```

This structural shift means **any LTTD model using fixed 50/200-day lookbacks will over-trade**. The signal horizon must scale with the expanding half-life. Current epoch: **120–350 days**.

### Dominant Spectral Frequency

FFT analysis of BTC daily log returns reveals a dominant power peak at **~1,268 days (3.47 years)** — closely matching the halving cycle. The LTTD signal is calibrated to this dominant spectral frequency.

### Glassnode Feature Discovery Alignment

Systematic bottom-up feature discovery (Glassnode 2025) found that optimal BTC uptrend detection uses **context windows of 800–1,200 days** — far longer than conventional periods. On-chain rolling statistics in this system use a minimum lookback of 800 days.

---

## Layer 1: Regime Detection

The first inference the system makes is: *what kind of market is this?*

A **3-state Gaussian Hidden Markov Model (HMM)** is trained on daily log returns and 20-day realized volatility. It infers the latent market regime at each daily step.

```python
# Inputs to HMM (no price indicators — pure statistical properties)
features = np.column_stack([
    log_returns,          # Daily price changes (log scale)
    realized_vol_20d,     # 20-day annualized realized volatility
])

# 3-state Gaussian HMM
model = GaussianHMM(n_components=3, covariance_type="full", n_iter=1000)
```

| Regime | Characteristics | LTTD Action |
|---|---|---|
| **BULL** | High returns, elevated volatility | Full ensemble active, max exposure |
| **BEAR** | Negative returns, high vol, rapid moves | Ensemble active, short bias |
| **SIDEWAYS** | Near-zero returns, low vol, no direction | **Ensemble disabled — zero position** |

> The most expensive mistake in trend-following is paying whipsaw costs during sideways consolidation. The HMM is the circuit breaker.

---

## Layer 2: Signal Engine

### Technical Indicators (12)

Each indicator outputs a binary directional score ∈ {-1, +1}. All are implemented with `CausalFilter` — **only past bars referenced; no symmetric windows**.

| # | Indicator | Category | Core Logic |
|---|---|---|---|
| 1 | **Kalman Filtered RSI** | Momentum/Trend | N-order Kalman on OHLC4 → RSI(250) → normalized [-0.5, 0.5] |
| 2 | **Momentum Zenith (LinReg Oscillator)** | Momentum | LinReg deviation + VWAP divergence → centered oscillator |
| 3 | **Adaptive Supertrend** | Trend | Highest-high channel × multiplier → directional signal |
| 4 | **FDI Adaptive Oscillator** | Trend/Momentum | Fractal Dimension Index regime filter + RSI/CCI consensus |
| 5 | **Adaptive Fourier Supertrend** | Spectral/Trend | DFT harmonic decomposition → volatility-band trend channel |
| 6 | **Relative Trend Index (RTI)** | Trend Strength | Sorted 2σ channel boundaries → percentile position signal |
| 7 | **MadTrend** | Trend | Multi-MA consensus with volatility normalization |
| 8 | **Quantile DEMA Supertrend** | Trend/Volatility | DEMA + percentile ATR bands → directional flip |
| 9 | **Inverted SD-DEMA RSI** | Momentum | DEMA + std dev envelope → RSI threshold crossing |
| 10 | **Stochastic ForLoop** | Momentum | Ensemble of Stoch(1..129) → average directional score |
| 11 | **VWMA Trend Strength Index** | Volume/Trend | (Close − VWMA) / ATR → z-scored trend intensity |
| 12 | **Savitzky Flow Bands** ⚠️ | Smoothing | **REMOVED — lookahead bias; see Pine Script Audit** |

> **Why only 11 active?** Indicator 12 (Savitzky-Golay) was identified as having a fatal lookahead bias in the original Pine Script. It is excluded from the Python implementation. See the [Pine Script Audit](#pine-script-audit) section.

### On-Chain Metrics (4) — via BRK API

All 4 metrics fetched live from `https://bitview.space`. **No API key required.**

| Series Name | Metric | Bullish Regime Signal |
|---|---|---|
| `sth_mvrv` | STH Market Value to Realized Value | < 1.0 (STH cost basis > price → capitulation) |
| `sth_nupl` | STH Net Unrealized Profit/Loss | < 0 (STH underwater → oversold) |
| `sth_sopr_24h` | STH Spent Output Profit Ratio (24h) | Bounce off 1.0 → trend continuation |
| `sth_supply_in_profit` | STH Supply Held at Profit | Low absolute level → cycle bottom proximity |

**Lead-lag behavior (research finding):**

| At Cycle Tops | At Cycle Bottoms |
|---|---|
| MVRV/NUPL **lead** price by 3–14 days | MVRV/NUPL **coincide or lag** |
| Use as regime filter, not execution trigger | Capitulation is fast — liquidations settle on-chain later |

> **Usage rule:** On-chain metrics act as **regime filters** (scale down max leverage when NUPL > 0.75 or STH-MVRV > 2.0), not as entry/exit triggers.

---

## Layer 3: Feature Processing

The central statistical problem: **12 technical indicators measuring the same underlying momentum signal will have VIF > 10.** Simple averaging of correlated inputs creates false confidence and synchronized failure during regime transitions.

### PCA Orthogonalization Pipeline

```python
# Step 1: Z-score standardize all N indicators
X_std = (X - X.mean(axis=0)) / X.std(axis=0)

# Step 2: Compute covariance matrix
Σ = (1/n) * X_std.T @ X_std

# Step 3: Eigendecomposition
eigenvalues, eigenvectors = np.linalg.eigh(Σ)

# Step 4: Select top k components (≥85% variance explained)
k = np.argmax(np.cumsum(eigenvalues[::-1]) / eigenvalues.sum() >= 0.85) + 1

# Step 5: Project → orthogonal, zero-multicollinearity features
PC = X_std @ eigenvectors[:, -k:]
```

**Expected output:** The first 3 principal components capture >85% of the variance from 16 input features — the remaining 13 are noise, not signal.

### Pratt's Relative Importance

After PCA, Pratt's measure (`dⱼ = βⱼ · rⱼ / R²`) identifies which original indicators contribute to the PC directions. Features with negative or near-zero Pratt measure are pruned.

---

## Layer 4: Ensemble Aggregation

### L1-Lasso Logistic Regression

```python
from sklearn.linear_model import LogisticRegression

model = LogisticRegression(
    penalty='l1',
    solver='liblinear',
    C=1/lambda_,       # lambda_ tuned via WFO validation set
    random_state=42
)

# Target: binary uptrend over next N-day horizon (epoch-adaptive)
# Features: PC₁, PC₂, PC₃ from Layer 3
model.fit(PC_train, y_train)
```

The **L1 penalty** simultaneously aggregates and prunes — redundant indicator components get their β coefficient shrunk to exactly zero, leaving only the most robust, non-correlated signal drivers.

### Walk-Forward Optimization (WFO)

```
Backtest window:   2017 ─────────────────────────── 2026

Fold 1:  [──TRAIN──────────────][──VAL──][TEST]
Fold 2:        [──TRAIN──────────────][──VAL──][TEST]
Fold 3:              [──TRAIN──────────────][──VAL──][TEST]
...
         ← 3yr train →← 6mo val →← 6mo test →  (rolling)
```

No static in-sample fit. Model parameters update on every fold. The reported backtest metrics use only out-of-sample test periods.

---

## On-Chain Data — bitview.space BRK API

[Bitcoin Research Kit (BRK)](https://github.com/bitcoinresearchkit/brk) is a free, open-source, MIT-licensed Bitcoin on-chain analytics API. `bitview.space` is the official hosted instance.

```
┌────────────────────────────────────────────────────────┐
│               BITVIEW.SPACE BRK API                     │
│                                                        │
│  49,000+ time-series  ·  No auth required              │
│  JSON + CSV output    ·  mempool.space compatible      │
│  Python client: brk-client (pip install brk-client)    │
└────────────────────────────────────────────────────────┘
```

### Quick Reference

```bash
# Search for available series
curl "https://bitview.space/api/series/search?q=sth_mvrv"

# Fetch last 1000 days of all 4 LTTD on-chain metrics in one request
curl "https://bitview.space/api/series/bulk?index=day\
      &series=sth_mvrv,sth_nupl,sth_sopr_24h,sth_supply_in_profit\
      &start=-1000"

# Latest single value
curl "https://bitview.space/api/series/sth_mvrv/day/latest"
```

### Response Shape

```json
{
  "version": 163,
  "index": "day1",
  "stamp": "2026-06-06T17:18:42Z",
  "start": 6359,
  "end": 6366,
  "data": [0.9634, 0.9334, 0.8799, 0.8571, 0.8423, 0.8251, 0.8223]
}
```

> **Critical:** Always validate `stamp` field ≥ yesterday before feeding data into the ensemble. The BRK stamp is derived from confirmed on-chain state — do not assume it equals `datetime.now()`.

### Live Values (2026-06-06)

| Metric | Series | Value | Interpretation |
|---|---|---|---|
| STH-MVRV | `sth_mvrv` | 0.822 | < 1.0 → STH at a loss (historically: early bull or bottom) |
| STH-NUPL | `sth_nupl` | -0.216 | Negative → STH hold unrealized losses |
| STH-SOPR | `sth_sopr_24h` | 0.984 | < 1.0 → selling below cost basis |
| STH Supply in Profit | `sth_supply_in_profit` | 81,897 BTC | Relatively low |

---

## Pine Script Audit

The original system was prototyped in `0xbujang-lttd.pinescript` — a 1,900-line Pine Script strategy aggregating 12 technical + 4 on-chain indicators. The exhaustive research audit identified **3 fatal flaws** that invalidate its backtest results.

### 🔴 Fatal Flaw 1: Savitzky-Golay Lookahead Bias (Indicator 12)

The SGF implementation in `savitzky_golay_filter_w_15_vectors()` uses a coefficient loop structure that produces a near-zero-lag curve in TradingView's historical replay mode. This is mathematically impossible in real-time execution — a causal filter cannot have zero lag. In live trading, the filter produces heavily lagged signals while the backtest shows perfect top/bottom timing.

**Fix:** Remove Indicator 12 entirely. Use the Adaptive Fourier Transform Supertrend (Indicator 5) for zero-lag cycle-tuned smoothing.

### 🔴 Fatal Flaw 2: Hardcoded On-Chain Date Arrays

On-chain signals (F1–F4) are encoded as static string arrays:

```pinescript
var string[] F1_data = array.from("2015-09-10|1", "2015-09-12|1", ... "2024-10-25|-1")
```

After the last date entry, `F1_score` defaults to `0`. The strategy **silently becomes purely technical in live trading** with no error or warning. All backtest on-chain performance is non-reproducible.

**Fix:** Fetch live via BRK API. Use `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`.

### 🔴 Fatal Flaw 3: Multicollinearity (12 Correlated Indicators)

Nine of twelve technical indicators are variations of momentum computed on RSI/DEMA/VWMA:

```python
# The simple average in Pine Script
final_score := sum_scores / count_indicators   # ← treats VIF-10 indicators as independent
```

When a regime shift occurs, all 12 simultaneously flip from +1 to -1. The mean model assigns full confidence to what is effectively one signal sampled 12 times. **VIF analysis would show 9 of 12 with VIF > 10.**

**Fix:** PCA orthogonalization + L1-Lasso to prune redundant components to zero.

---

## Getting Started

### Prerequisites

- Python 3.11+
- `pip` (package manager)
- No external API keys required — BRK data is free

### Installation

```bash
git clone https://github.com/lutfi-zain/quant-btc-lttd-system.git
cd quant-btc-lttd-system

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
python -m pip install -r requirements.txt
```

### Core Dependencies

```txt
# requirements.txt
pandas>=2.0
numpy>=1.26
scipy>=1.12
scikit-learn>=1.4
hmmlearn>=0.3
xgboost>=2.0
brk-client>=0.3.2        # bitview.space on-chain data
matplotlib>=3.8
plotly>=5.20
pytest>=8.0
pytest-cov>=5.0
```

### Verify On-Chain Feed

```bash
# Confirm BRK data is accessible (no API key needed)
python -c "
import requests
resp = requests.get(
    'https://bitview.space/api/series/bulk',
    params={
        'index': 'day',
        'series': 'sth_mvrv,sth_nupl,sth_sopr_24h,sth_supply_in_profit',
        'start': -5
    }
)
for s in resp.json():
    print(s['index'], '→', s['data'][-1])
"
```

### Run Tests

```bash
# Fast validation
python -m pytest -xvs

# Full validation with coverage
python -m pytest --cov

# Single layer test
python -m pytest -xvs tests/test_regime.py
```

---

## Project Structure

```
quant-btc-lttd-system/
│
├── backend/                             # Hono v4 API (Bun runtime)
│   ├── index.ts                         # All REST endpoints
│   ├── db.ts                            # SQLite connection (WAL mode)
│   ├── package.json                     # Bun dependencies
│   └── tsconfig.json
│
├── frontend/                            # React SPA (Vite + TypeScript)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts                # Fetch hooks for all endpoints
│   │   ├── types/lttd.ts                # Shared TypeScript interfaces
│   │   └── components/
│   │       ├── RegimeBanner.tsx         # BULL / BEAR / SIDEWAYS status
│   │       ├── ScoreGauge.tsx           # Final Score arc gauge
│   │       ├── ScoreChart.tsx           # Final Score time-series
│   │       ├── BtcPriceChart.tsx        # OHLC + regime overlay bands
│   │       ├── OnChainPanel.tsx         # 4 STH metric subplots
│   │       ├── IndicatorStack.tsx       # 11 indicator score cards
│   │       ├── PcaPanel.tsx             # PC loadings + variance
│   │       ├── WfoPanel.tsx             # WFO fold table
│   │       └── RegimeTimeline.tsx       # Bull/Bear/Sideways history
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── database/                            # SQLite persistence
│   ├── db.py                            # Python DB connection
│   └── schema.sql                       # Table definitions
│
├── src/
│   ├── regime/                      # Layer 1: HMM regime classification
│   │   ├── hmm_model.py             # 3-state Gaussian HMM
│   │   ├── state_classifier.py      # Posterior probability → regime label
│   │   └── regime_transitions.py    # Transition logging
│   │
│   ├── signals/                     # Layer 2: Causal indicator engine
│   │   ├── base.py                  # CausalFilter abstract base class
│   │   ├── technical/               # 11 technical indicators (no SGF)
│   │   │   ├── kalman_rsi.py        # Indicator 1
│   │   │   ├── linreg_zenith.py     # Indicator 2
│   │   │   ├── adaptive_supertrend.py  # Indicator 3
│   │   │   ├── fdi_oscillator.py    # Indicator 4
│   │   │   ├── fft_supertrend.py    # Indicator 5
│   │   │   ├── rti.py               # Indicator 6
│   │   │   ├── madtrend.py          # Indicator 7
│   │   │   ├── quantile_dema.py     # Indicator 8
│   │   │   ├── sd_dema_rsi.py       # Indicator 9
│   │   │   └── stoch_forloop.py     # Indicator 10
│   │   │   └── vwma_tsi.py          # Indicator 11
│   │   └── onchain/                 # 4 on-chain metric signals
│   │       ├── brk_feed.py          # BRK API client (typed interface)
│   │       ├── sth_mvrv.py          # STH-MVRV signal
│   │       ├── sth_nupl.py          # STH-NUPL signal
│   │       ├── sth_sopr.py          # STH-SOPR (sth_sopr_24h)
│   │       └── supply_profit.py     # STH Supply in Profit
│   │
│   ├── features/                    # Layer 3: PCA + VIF orthogonalization
│   │   ├── standardizer.py          # Z-score standardization
│   │   ├── vif_filter.py            # Variance Inflation Factor check
│   │   ├── pca_engine.py            # PCA orthogonalization
│   │   └── pratt_measure.py         # Pratt's relative importance
│   │
│   ├── ensemble/                    # Layer 4: L1-Lasso + WFO
│   │   ├── lasso_model.py           # L1-regularized logistic regression
│   │   ├── wfo.py                   # Walk-forward optimization
│   │   └── score_engine.py          # Final Score ∈ [-1.0, +1.0]
│   │
│   └── execution/                   # Layer 5: Regime-weighted sizing
│       ├── position_sizer.py        # Regime posterior × Final Score
│       └── signal_publisher.py      # Output: BULL / BEAR / SIDEWAYS
│
├── tests/                           # pytest test suite
│   ├── test_no_lookahead.py         # ⭐ Lookahead bias detection for all indicators
│   ├── test_regime.py               # HMM state transition tests
│   ├── test_features.py             # PCA + VIF tests
│   ├── test_ensemble.py             # WFO fold validation
│   └── test_brk_feed.py             # BRK API integration tests
│
├── openspec/                        # Change management (OpenSpec)
│   ├── config.yaml                  # Schema + context + per-artifact rules
│   ├── specs/                       # Source-of-truth behavioral specs
│   └── changes/                     # In-progress + archived changes
│
├── 0xbujang-lttd.pinescript         # Legacy Pine Script (audit reference only)
├── pi_final_research_lttd_01.md     # Exhaustive research report (98% confidence)
├── AGENTS.md                        # AI agent guardrails & DDD ubiquitous language
├── requirements.txt
└── README.md
```

---

## Dashboard & API

Same proven stack as `quant-btc-valuation-system` and `lttf-system`.

```
┌────────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                                  │
│                                                                         │
│  Python Engine ──→ SQLite (WAL) ──→ Hono v4 API ──→ React SPA         │
│  (Layers 1–5)       lttd.db        (Bun runtime)    (Vite + TS)        │
└────────────────────────────────────────────────────────────────────────┘
```

### Backend — Hono v4 API (Bun)

| Endpoint | Description | Response |
|---|---|---|
| `GET /api/ping` | Health check | `{status, db_rows}` |
| `GET /api/regime` | Current HMM regime + posteriors | `{regime, p_bull, p_bear, p_sideways, stamp}` |
| `GET /api/score` | Final Score time-series | `{data: [{date, score, direction}]}` |
| `GET /api/score/latest` | Current Final Score | `{score, direction, regime, stamp}` |
| `GET /api/indicators` | All 11 technical indicator scores | `{data: [{name, score, category}]}` |
| `GET /api/onchain` | 4 on-chain metrics history | `{data: [{date, sth_mvrv, sth_nupl, sth_sopr_24h, sth_supply_in_profit}]}` |
| `GET /api/pca` | PCA component loadings | `{components, explained_variance, pratt_measures}` |
| `GET /api/wfo` | Walk-forward fold results | `{folds, summary: {mean_sharpe, mean_accuracy}}` |
| `GET /api/regime/history` | HMM state history | `{data: [{date, regime, p_bull, p_bear, p_sideways}]}` |
| `GET /api/ohlc` | BTC daily OHLC | `{data: [{date, open, high, low, close}]}` |

### Frontend — React SPA Components

| Component | Purpose |
|---|---|
| `RegimeBanner` | Large status card — BULL · BEAR · SIDEWAYS with posterior probabilities |
| `ScoreGauge` | Animated arc gauge showing Final Score ∈ [-1.0, +1.0] |
| `ScoreChart` | Lightweight Charts line — Final Score history with regime color fills |
| `BtcPriceChart` | OHLC candlestick with HMM regime overlay bands |
| `OnChainPanel` | 4 subplot series: STH-MVRV, STH-NUPL, STH-SOPR, Supply in Profit |
| `IndicatorStack` | Grid of 11 indicator score cards (+1 green / -1 red) |
| `PcaPanel` | PC component loadings bar chart + explained variance |
| `WfoPanel` | Walk-forward fold table (train/test Sharpe per fold) |
| `RegimeTimeline` | Horizontal stacked bar — Bull/Bear/Sideways % by year |

### Database Schema (SQLite WAL)

```sql
-- Core time-series output
CREATE TABLE daily_lttd (
  date          TEXT PRIMARY KEY,
  final_score   REAL,          -- ∈ [-1.0, +1.0]
  regime        TEXT,          -- 'BULL' | 'BEAR' | 'SIDEWAYS'
  p_bull        REAL,          -- HMM posterior
  p_bear        REAL,
  p_sideways    REAL
);

-- Per-indicator scores
CREATE TABLE indicator_scores (
  date           TEXT,
  indicator_name TEXT,
  score          INTEGER,      -- -1 or +1
  PRIMARY KEY (date, indicator_name)
);

-- On-chain metric values (from BRK API)
CREATE TABLE onchain_metrics (
  date                   TEXT PRIMARY KEY,
  sth_mvrv               REAL,
  sth_nupl               REAL,
  sth_sopr_24h           REAL,
  sth_supply_in_profit   REAL,
  stamp                  TEXT   -- BRK response stamp
);

-- WFO fold results
CREATE TABLE wfo_folds (
  fold_id        INTEGER PRIMARY KEY,
  train_start    TEXT,
  train_end      TEXT,
  test_start     TEXT,
  test_end       TEXT,
  test_accuracy  REAL,
  test_sharpe    REAL,
  lambda_        REAL   -- best L1 regularization strength
);
```

---

## OpenSpec Workflow

This repository uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for structured change management. Every feature, fix, or refactor follows the artifact pipeline before implementation.

```
/opsx:propose         →  Create change + all artifacts in one step
/opsx:new             →  Scaffold a change folder
/opsx:ff              →  Fast-forward: proposal → specs → design → tasks
/opsx:apply           →  Implement tasks
/opsx:verify          →  Validate implementation vs specs
/opsx:archive         →  Merge delta specs + archive change
```

**Artifact flow:**

```
proposal ──→ specs ──→ design ──→ tasks ──→ implement ──→ verify ──→ archive
  why          what      how       steps       code        check      merge
```

All proposals in this repository must include:
- Mathematical/statistical motivation for the change
- Affected layer(s) from the 5-layer architecture
- VIF argument (if adding any new indicator)
- Estimated Sharpe/MaxDD impact

---

## Academic References

1. **Springer (2026)** — "Regime-Aware Adaptive Forecasting Framework for Bitcoin Prices." *Computational Economics*. [DOI](https://link.springer.com/article/10.1007/s10614-026-11338-3) — HMM + regime-specialized models achieve R²=0.93
2. **Glassnode Research (2023)** — "An Automated Trading Strategy Grounded in Machine Learning and On-Chain Analytics." [link](https://research.glassnode.com/the-predictive-power-of-glassnode-data) — Supervised ML on on-chain features
3. **Glassnode Insights (2025)** — "Systematic Feature Discovery for Digital Asset Markets." [link](https://insights.glassnode.com/systematic-feature-discovery-for-digital-assets) — 800–1,200 day optimal windows
4. **SSRN (2025)** — "Quantitative Evaluation of Volatility-Adaptive Trend-Following in Cryptocurrency Markets." [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5821842)
5. **Moskowitz, T.J., Ooi, Y.H. & Pedersen, L.H.** (2012). "Time Series Momentum." *Journal of Financial Economics*, 104(2), 228–250.
6. **Pratt, J.W.** (1987). "Dividing the Indivisible." *Proceedings of the First International Tampere Seminar on Linear Statistical Models* — relative importance in regression
7. **QuantPedia** — "Revisiting Trend-following and Mean-reversion Strategies in Bitcoin." [link](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin)
8. **Alpha Architect** — "Optimal Trend-Following Rules in Two-State Regime-Switching Models." [link](https://alphaarchitect.com/optimal-trend-following-rules-in-two-state-regime-switching-models)
9. **DSP StackExchange** — "Savitzky-Golay filtering (not smoothing) in real time." [link](https://dsp.stackexchange.com/questions/83038) — mathematical proof of causal constraint
10. **Bitcoin Research Kit (BRK)** — Open-source on-chain analytics API. [GitHub](https://github.com/bitcoinresearchkit/brk) · [bitview.space](https://bitview.space)

---

## License

MIT © [lutfi-zain](https://github.com/lutfi-zain)

---

<div align="center">
  <sub>Built with Python, scikit-learn, hmmlearn, and 📊 | On-chain data from bitview.space (BRK) | No lookahead. No hardcoded signals. No excuses.</sub>
</div>
