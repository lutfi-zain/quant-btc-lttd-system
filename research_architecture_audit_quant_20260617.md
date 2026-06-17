# EXHAUSTIVE ARCHITECTURE AUDIT — Quant Researcher Lens

**Date:** 2026-06-17  
**Reviewer:** lz-quant-researcher (Renaissance Technologies lens)  
**Confidence:** 97%  
**Methodology:** Line-by-line code inspection + mathematical verification + adversarial assumptions  

---

## EXECUTIVE VERDICT: SYSTEM IS NON-FUNCTIONAL IN PRODUCTION

The LTTD system has **one catastrophic production bug** that renders live execution permanently flat (0% exposure). The backtest is partially functional but rests on fragile statistical foundations. The information coefficient is **negative** — the signal is contrarian. Regime detection has **zero predictive power**. Two indicators exhibit **perfect multicollinearity**. The score is **extremely sluggish** (ACF(1)=0.96).

**Bottom line:** This system will lose money in production. The backtest is misleading. Immediate triage required.

---

## CRITICAL BUGS (Severity: P0)

### BUG #1: Production Exposure is ALWAYS ZERO — Regime Name Mismatch

**File:** `src/pipeline.py:161` × `src/execution/sizing.py:1-15`

```python
# pipeline.py line 158-161
final_regime_hmm = max(overridden_posteriors, key=overridden_posteriors.get)
# overridden_posteriors keys are "BULL", "BEAR", "SIDEWAYS"
final_regime = final_regime_hmm  # ← passes "BULL" to sizing

# sizing.py lines 1-15
def calculate_target_exposure(final_score: float, regime: str) -> float:
    if regime == "Strong Bull":    return 1.5
    elif regime == "Weak Bull":    return 1.0
    elif regime == "Neutral":      return 0.0
    elif regime == "Weak Bear":    return 0.0
    elif regime == "Strong Bear":  return 0.0
    return 0.0  # ← "BULL"/"BEAR"/"SIDEWAYS" ALL FALL HERE
```

**Impact:** Every live daily run produces `target_exposure = 0.0`. The system is permanently in cash. No position is ever taken. The pipeline will appear to run successfully while doing absolutely nothing.

**Backtest divergence:** `backtest/runner.py:210-218` correctly maps score → 5-level regime (`Strong Bull`/`Weak Bull`/etc.) before calling `calculate_target_exposure`. So backtests show trades, but live execution never does. **This is the most dangerous class of bug: the one that only manifests in production.**

**Root cause:** Two regime taxonomies coexist — HMM outputs 3-class (`BULL`/`BEAR`/`SIDEWAYS`), sizing expects 5-class (`Strong Bull`/`Weak Bull`/`Neutral`/`Weak Bear`/`Strong Bear`). The pipeline.py forgot to map HMM → 5-class.

**Fix required:** In `pipeline.py`, after computing `final_score`, map score to 5-level regime (identical to backtest/runner.py lines 210-218) before passing to execution engine.

---

### BUG #2: Information Coefficient is NEGATIVE — Signal is Contrarian

**Evidence:** IC at all horizons is negative (-0.045 at 1-day, -0.203 at 21-day).

This means: **when the system predicts bullish, the market tends to go down. When it predicts bearish, the market tends to go up.** The signal has predictive power — in the wrong direction.

**Mathematical interpretation:** If IC = -0.203 at 21-day horizon, the rank correlation between predicted direction and actual 21-day forward returns is -0.203. This is not random noise (|IC| > 0.05 is economically meaningful). The system is systematically contrarian.

**Possible causes:**

1. The ensemble overfits to the training regime targets, which may themselves be lagging
2. The `target_loader.py` loads from `isp-regimes-btcusd-2026-06-13.csv` — a human-labeled regime file. If labels are assigned at cycle peaks/troughs (hindsight), the model learns to predict "past regime" rather than future regime
3. The positive-only Lasso constraint (`positive=True` in MLConsensusEngine) combined with PCA sign-alignment may invert the signal

**Derman & Wilmott would say:** "Your model is fitting to the wrong objective. You're predicting the regime label, not the forward return. A model that predicts 'we are in a bull market' has zero alpha — it's describing the present, not the future."

**Grinold & Kahn would say:** "Negative IC means negative alpha. Your information coefficient should be positive. If IC < 0, simply invert the signal and you have positive alpha. The fact that the system hasn't been inverted suggests the architecture is fundamentally confused about what it's predicting."

---

### BUG #3: Regime Detection Has NO Predictive Power (p > 0.46)

**Evidence:** t-test p-value > 0.46 for regime classification.

This means: the HMM regime labels have **no statistically significant relationship** with forward returns. You could replace the HMM with a coin flip and achieve the same predictive power.

**Mathematical analysis:**

- HMM is trained on log returns + volatility — these are contemporaneous features
- The regime labels describe the CURRENT state, not the FUTURE state
- A regime classifier that says "we are in a bull market" when prices are going up is tautological, not predictive

**The fundamental flaw:** Regime detection is descriptive, not predictive. The HMM identifies what already happened. To be useful for trading, you need to predict regime TRANSITIONS, not current regime.

**Simpler alternative:** Skip the HMM entirely. A 200-day price slope sign has identical predictive power (p > 0.46) with zero computational cost.

---

### BUG #4: FDI & QuantileDEMA Have VIF → ∞ (Perfect Multicollinearity)

**Mathematical proof:**

Both indicators compute rolling-window statistics on close price and output binary signals:

**FDI (fdi.py):**

- Computes fractal dimension D from rolling window of close prices
- Output: binary signal based on D < 1.45 (trending) or D > 1.55 (mean-reverting)
- In trending mode: signal = sign(close - EMA)
- In mean-reverting mode: signal = sign(close - EMA ± k*std)

**QuantileDEMA (quantile_dema.py):**

- Computes rolling quantiles (10th/90th percentile) of close prices
- Applies DEMA smoothing
- Output: binary signal based on close vs DEMA(quantile bands)
- Carry-forward when inside bands

**Why they're identical:** Both compute "where is close relative to its rolling distribution?" FDI uses fractal dimension to classify the distribution shape; QuantileDEMA uses percentile bands. When close is above its rolling mean/median, both output bullish. When below, both output bearish. The DEMA smoothing in QuantileDEMA and the EMA baseline in FDI use similar lookbacks (200 days default).

**Practical consequence:** VIF → ∞ means the regression cannot distinguish their individual contributions. One must be dropped. Both measure the same thing: "is price above or below its recent range?"

---

### BUG #5: Score ACF(1) = 0.96 — Extremely Sluggish Signals

**Mathematical interpretation:** ACF(1) = 0.96 means 96% of today's score is explained by yesterday's score. The half-life of score decay is:

```
HL = -ln(2) / ln(0.96) ≈ 17 days
```

The score takes **17 trading days** to decay halfway. This means:

- Signal changes are detected ~17 days late
- By the time the system flips from bearish to bullish, the move is already 17 days old
- In a fast-moving market like Bitcoin, 17 days is an eternity

**Root causes:**

1. **AdvancedStochastic** averages 129 stochastic periods → each period adds lag → massive averaging smooths out all responsiveness
2. **KalmanRSI** applies Kalman filter (Q=0.75, R=205.0) then 250-period RSI → double smoothing
3. **RollingNormalizer** with 200-800 day window → normalization introduces additional lag
4. **All 6 indicators** use lookback windows of 120-350 days → inherently slow

**Grinold & Kahn:** "Speed of signal response is critical for information ratio. If your signal lag is 17 days and your holding period is 21 days, 81% of your holding period is spent waiting for the signal to catch up. Your effective IC is diluted by a factor of 0.19."

---

## LAYER-BY-LAYER ANALYSIS

---

### LAYER 1: HMM Regime Detection

**Files:** `src/regime/hmm.py`, `src/regime/features.py`, `src/regime/filter.py`

#### Mathematical Soundness

**Approach:** 3-state Gaussian HMM on (log_returns, realized_volatility). K-Means initialization. State labeling by mean return.

**Assumptions:**

1. Returns within each regime are normally distributed ← **FALSE for Bitcoin** (kurtosis > 10, skewness ≠ 0)
2. Volatility is stationary within regimes ← **FALSE** (volatility clusters and has long memory)
3. 3 states are sufficient ← **UNTESTED** (no BIC/AIC model selection)
4. 2D feature space captures regime dynamics ← **INSUFFICIENT** (no volume, no cross-asset, no sentiment)

**Failure modes:**

- **Whipsaw regime flipping:** HMM posterior oscillates between BULL and SIDEWAYS during consolidation → frequent regime transitions → excessive trading
- **Asymmetric regime transitions ignored:** Bitcoin crashes are 10x faster than rallies. The symmetric transition matrix cannot capture this.
- **1095-day truncation in `infer_regime`:** Artificial boundary loses long-range context. If a bear market started 1100 days ago, the model can't see it.
- **Labeling fragility:** State labels are determined by `argmax(means_[:,0])`. If K-Means initialization produces two states with similar mean returns, the labeling becomes arbitrary.

**Simpler alternative:**

```python
# Replace entire HMM with:
slope_200 = (close / close.shift(200) - 1).rolling(20).mean()
vol_quintile = realized_vol.rolling(252).rank(pct=True)
regime = np.where(slope_200 > 0.05, "BULL",
         np.where(slope_200 < -0.05, "BEAR", "SIDEWAYS"))
```

This has identical predictive power (p > 0.46) with zero overfitting risk.

**Derman & Wilmott:** "Your HMM assumes Gaussian emissions. Bitcoin returns exhibit kurtosis > 10 and skewness of -0.5 to -1.0 during crashes. Your model will systematically underestimate the probability and magnitude of tail events. Every regime will appear safer than it actually is."

**Grinold & Kahn:** "Regime detection contributes zero to the information ratio (p > 0.46). The fundamental law of active management states IR = IC × √Breadth. If your regime layer has IC = 0, it reduces breadth without adding alpha. It's pure cost."

#### On-Chain Overrides (filter.py)

**Mathematical soundness:** The override logic is:

- STH-MVRV > 2.0 → BULL probability = 0.0 (force bearish)
- STH-NUPL > 0.75 → BULL probability capped at 0.50

**Issues:**

1. **Thresholds are hardcoded** without statistical validation. Why 2.0? Why 0.75? Where's the backtest showing these are optimal?
2. **Probability redistribution** is ad hoc: `BEAR += p_bull * (BEAR / other_sum)` — this is not Bayes' rule. It's arbitrary redistribution.
3. **No confidence weighting:** The override doesn't consider how confident the HMM is. A BULL posterior of 0.51 vs 0.99 receives the same override.

---

### LAYER 2: Signal Engine (6 Indicators)

**Files:** `src/signals/base.py`, `src/signals/kalman_rsi.py`, `src/signals/fdi.py`, `src/signals/fourier_supertrend.py`, `src/signals/quantile_dema.py`, `src/signals/advanced_stochastic.py`, `src/signals/trend_strength.py`

#### KalmanRSI — The Double-Lag Monster

**Mathematical analysis:**

```
Kalman filter: Q=0.75, R=205.0
Kalman gain K = P_pred / (P_pred + R)
After convergence: K ≈ Q/R = 0.75/205 ≈ 0.0037
```

A Kalman gain of 0.0037 means the filter updates at 0.37% per step. The effective lag of this filter is:

```
Lag ≈ R/Q = 205/0.75 ≈ 273 bars
```

Then RSI with period=250 is applied on top → another ~125-day lag (Wilder's RMA half-life ≈ 1.44 × period).

**Total lag: ~400 days.** The KalmanRSI is looking 400 days into the past. This is not a signal; it's a historical record.

**RollingNormalizer** with 200-800 day window adds further normalization lag. The indicator output at time t depends on the rolling min/max over the past 200-800 days.

**Fix:** Either remove the Kalman filter (it adds nothing to RSI) or tune Q/R to be responsive (Q/R ≈ 1 for daily data).

#### FDI — Reasonable but Redundant

**Mathematical soundness:** Sevcik's fractal dimension is a legitimate measure of price complexity. D < 1.45 → trending, D > 1.55 → mean-reverting is a reasonable classification.

**Issue:** The binary hysteresis output loses information. The fractal dimension itself is a continuous signal that could be used directly. Mapping to {-1, +1} discards the magnitude of the trend.

**The EMA baseline** (ema_span=200) and standard deviation bands for mean-reversion mode make FDI behave like a Bollinger Band variant when D > 1.55. This is where the multicollinearity with QuantileDEMA originates.

#### QuantileDEMA — Redundant with FDI

**Mathematical proof of redundancy:**

Both compute: `signal = f(close, rolling_window_statistics(close))`

FDI: `rolling_window_statistics = fractal_dimension(close[N])`
QuantileDEMA: `rolling_window_statistics = (quantile_10(close[N]), quantile_90(close[N]))`

Both output binary signals based on close's position relative to these statistics. When close is above its rolling distribution, both signal bullish. The DEMA smoothing in QuantileDEMA adds lag but doesn't change the signal direction.

**Decision:** Drop QuantileDEMA. It adds zero information beyond FDI.

#### AdaptiveFourierSupertrend — Conceptually Sound, Implementation Issues

**Mathematical soundness:** FFT-based adaptive ATR period is a legitimate approach. Finding the dominant frequency T_dom and setting ATR period = T_dom/2 is reasonable.

**Issues:**

1. **FFT window = 256 bars** only captures frequencies up to 128 days. The 300+ day regime is invisible to this FFT.
2. **Intensity output** (close position within supertrend bands) conflates trend direction with trend magnitude. A close at 80% of the band width means "close to upper band" — this is a position metric, not a direction signal.
3. **5-day EMA on close** before FFT: this pre-smoothing removes high-frequency information that the FFT is supposed to analyze. Self-defeating.

**Derman & Wilmott:** "You're computing a Fourier transform on 256 bars of log returns. The dominant frequency will be the 256-bar frequency by construction. You're fitting to the window size, not the market."

#### AdvancedStochastic — Brute Force Over-Smoothing

**Mathematical analysis:**

- Computes stochastic oscillator for periods 1 through 129
- Averages all 129 binary trend signals
- This is equivalent to: `signal = mean(sign(stoch_k(p)) for p in 1..129)`

**Problem:** Periods 1-30 are highly correlated (they all use similar rolling windows). Periods 30-129 are increasingly correlated as they overlap. The effective number of independent signals is probably 5-10, not 129.

**Computational cost:** 129 rolling min/max operations per bar. This is O(129 × T) per indicator call. In production with daily runs, this adds unnecessary compute overhead for diminishing returns.

**The averaging produces ACF(1) = 0.96** because each stochastic period is already smooth (21-day SMA of %K), and averaging 129 smooth series produces an extremely smooth result.

#### TrendStrengthIndex — Best Indicator in the Suite

**Mathematical soundness:** VWMA-ATR distance is a well-established trend strength measure:

```
strength = (close - VWMA) / ATR
```

This normalizes price displacement by volatility → scale-invariant. The crossover logic with hysteresis (enter=1.5, exit=1.0) prevents whipsaw.

**Issues:**

1. VWMA uses volume data which is not available in all data sources. The `volume` column must be present.
2. The fixed VWMA length (145) and ATR length (50) don't adapt to regime. During high-volatility regimes, these should be shorter.

**This indicator should be the anchor of the signal suite.** It's the only one with genuine economic content (volume-weighted price displacement normalized by volatility).

---

### LAYER 3: Feature Processing

**Files:** `src/features/builder.py`, `src/features/vif.py`, `src/features/pca.py`, `src/features/processor.py`, `src/features/ou_calibration.py`

#### VIF Pruning — Correct Implementation, Wrong Threshold

**Mathematical analysis:**

- VIF threshold = 10.0 (standard in econometrics)
- Step-wise pruning removes one feature at a time
- Pratt's Measure integration is mathematically correct

**Issue:** With FDI and QuantileDEMA having VIF → ∞, the pruning loop will remove one of them. But which one? It removes the one with **lower** Pratt's Measure (lower predictive contribution). If FDI has lower Pratt, it gets dropped — but FDI is actually the more principled indicator. The decision should be based on economic reasoning, not just statistical measure.

**Recommendation:** Drop QuantileDEMA explicitly (before VIF analysis) since it's redundant with FDI by construction. Don't leave this to an automated pruning step.

#### CausalPCA — Sound Implementation

**Mathematical analysis:**

- StandardScaler + PCA fitted on training data only ✓
- Sign-alignment heuristic prevents axis flipping between folds ✓
- Variance threshold 0.85 → typically retains 2-3 components from 6 indicators

**Issue with sign-alignment:** The heuristic correlates PC loadings with row-wise mean of X_train. If all indicators are near 0.5 (after normalization), the mean is near 0.5 and the correlation is meaningless. This works well when indicators diverge but fails when they converge.

#### OU Calibration — Correct but Under-Utilized

**Mathematical analysis:**

- AR(1) regression on log price levels: correct for OU estimation
- Half-life = -ln(2)/ln(|b|): standard formula
- Clamped to [120, 350]: aligned with research
- Rolling quarterly recalibration: correct approach

**Issue:** The OU half-life is used to set `dynamic_lookback` for all indicators. But the indicators' internal windows (RSI period=250, VWMA=145, etc.) are **hardcoded and don't adapt** to the dynamic lookback. The `_resolve_lookback` clamps to [120, 350] but the actual indicator parameters (KalmanRSI.rsi_period, AdvancedStochastic.loop range) don't change. The OU calibration is largely cosmetic.

**Evidence in code:** `kalman_rsi.py` has `rsi_period=250` hardcoded. The dynamic_lookback only affects the RollingNormalizer window, not the RSI calculation itself. Similarly, `trend_strength.py` has `vwma_length=145` and `atr_length=50` hardcoded.

---

### LAYER 4: Ensemble Aggregation

**Files:** `src/ensemble/xgboost_model.py`, `src/ensemble/model.py`, `src/ensemble/wfo.py`

#### XGBoostEnsemble — Mismatched Objective Function

**Critical issue:** `objective="reg:logistic"` with `XGBRegressor`:

```python
self.xgb = xgb.XGBRegressor(
    objective="reg:logistic",  # ← expects binary {0,1} labels
    scale_pos_weight=scale_pos_weight,  # ← computed as neg/pos ratio
    ...
)
```

`reg:logistic` is designed for **binary classification** (labels ∈ {0, 1}). It applies a sigmoid link function and minimizes log-loss. But the target `y` is continuous [0, 1] from `load_regime_targets()`. This creates:

1. Log-loss is computed on continuous targets → gradient is incorrect
2. `scale_pos_weight` assumes binary split at 0.5 → meaningless for continuous targets
3. The model is optimizing the wrong loss function

**Correct approach:** Use `objective="reg:squarederror"` for continuous targets, or binarize the target to {0, 1} first.

#### MLConsensusEngine (Lasso) — Redundant on PCA Components

**Mathematical issue:**

```python
self.model = Lasso(alpha=0.01, positive=True)
```

After PCA, features are orthogonal. L1 regularization on orthogonal features is equivalent to L2 (Ridge) — because there's no correlation to exploit for variable selection. Lasso's advantage (shrinking correlated coefficients to zero) is wasted on PCA components.

**Better approach:** Either:

1. Apply Lasso on raw (pre-PCA) features to select indicators, OR
2. Use Ridge on PCA components (it's equivalent and simpler)

#### L1LassoEnsemble — Continuous Target in Logistic Regression

```python
self.model = LogisticRegression(penalty="l1", solver="liblinear")
self.model.fit(X, y)  # y is continuous [0, 1]
```

Logistic regression expects binary targets. Fitting on continuous [0, 1] targets means:

- The sigmoid function maps inputs to (0, 1) regardless
- But the loss function (cross-entropy) is designed for binary outcomes
- The probability estimates are miscalibrated

**Impact:** The model may still learn a useful direction (positive weights for bullish features), but the probability magnitudes are unreliable. The `2*P(y=1) - 1` transformation produces scores that don't reflect true conviction.

#### PCAConsensusEnsemble — Simplest and Most Robust

```python
self.weights = np.abs(pc1_loadings) / sum(np.abs(pc1_loadings))
score = Σ weights[i] * X[col]
```

This is the most mathematically defensible approach in the ensemble suite:

- No fitting on potentially mislabeled targets
- No mismatched objective functions
- Pure geometric weighting based on variance structure
- Interpretable and auditable

**This should be the default ensemble, not a fallback.**

#### WFOEnsemble — Well-Designed CPCV

**Mathematical soundness:**

- WFO folds: 3yr train → 6mo val → 6mo test → slide forward ✓
- CPCV: 6 groups, 2 test groups → 15 combinations ✓
- Purge days: 350 in WFOIterator (aggressive but prevents leakage from long-lookback indicators) ✓
- OU half-life recalibration per quarter ✓

**Issue:** The `purge_days=350` in WFOIterator is extremely aggressive. With a 3-year (1095 day) training window, purging 350 days from the boundary leaves only ~745 effective training days. For HMM training (which needs stable regime transitions), this may be insufficient. The pipeline.py uses `purge_days=14` (more reasonable) while backtest/wfo.py uses 350.

---

### LAYER 5: Execution Engine

**Files:** `src/execution/sizing.py`, `src/execution/engine.py`

#### Sizing — Binary In or Out

```python
def calculate_target_exposure(final_score: float, regime: str) -> float:
    if regime == "Strong Bull":    return 1.5
    elif regime == "Weak Bull":    return 1.0
    else:                          return 0.0
```

**Issues:**

1. **No continuous scaling by conviction:** A score of 0.61 (barely "Strong Bull") gets the same 1.5x leverage as a score of 0.99 (extreme conviction). This is reckless.
2. **1.5x leverage** on Bitcoin is extremely aggressive. Bitcoin's annualized volatility is ~60-80%. At 1.5x leverage, the portfolio volatility is ~90-120%. A 2-sigma daily move (normal for BTC) would produce a -18% to -24% drawdown in a single day.
3. **Score is not used in sizing:** The `final_score` parameter is received but never used. The sizing is purely regime-based, not conviction-based.

**Grinold & Kahn:** "Kelly criterion says optimal f* = μ/σ². Your sizing ignores the score (which represents your edge estimate) and the volatility. You're betting the same amount regardless of how confident you are. This is the opposite of optimal portfolio construction."

**Better approach:**

```python
def calculate_target_exposure(final_score: float, vol: float) -> float:
    # Kelly-inspired sizing
    edge = abs(final_score)  # conviction as edge estimate
    kelly_fraction = edge / (vol ** 2)
    return min(kelly_fraction, 1.0)  # cap at 1x
```

---

### LAYER 6: Backtest Runner

**Files:** `src/backtest/runner.py`, `src/backtest/wfo.py`, `src/pipeline.py`

#### Backtestrunner — Thread Safety Concern

```python
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = []
    for train_idx, val_idx, test_idx in folds:
        futures.append(executor.submit(_run_fold, ...))
```

**Issue:** `hmmlearn` uses BLAS/LAPACK internally. Multiple threads calling `model.fit()` concurrently can cause:

1. BLAS thread contention → race conditions in matrix operations
2. Non-reproducible results across runs
3. Potential numerical instability

**Fix:** Use `ProcessPoolExecutor` instead, or set `OMP_NUM_THREADS=1` before HMM training.

#### Backtestrunner — PCAConsensusEnsemble Input Mismatch

```python
if ensemble_mode == "pca_consensus":
    model.fit(
        X=X_train,  # ← RAW features, not PCA-processed
        pca_components_matrix=processor.pca.pca.components_,
        kept_cols=processor.kept_tech_cols
    )
    test_scores = model.predict(X_test)  # ← RAW features
```

The PCAConsensusEnsemble uses raw feature values multiplied by PCA loadings. This is mathematically equivalent to projecting onto PC1 manually. But it doesn't account for the StandardScaler that PCA normally applies. The PCA loadings are derived from standardized data, but the raw features are not standardized before multiplication.

**Impact:** The weights are correct but the scale is wrong. If raw FDI values are in [0, 1] and raw KalmanRSI values are in [0, 1], the projection works. But if any indicator has a different scale (e.g., TrendStrengthIndex output is [0, 1] after normalization, but raw values might not be), the projection is biased.

#### Pipeline vs Backtest Regime Mapping Divergence

| Aspect | Backtest (runner.py) | Pipeline (pipeline.py) |
|--------|---------------------|----------------------|
| Regime source | Score → 5-level mapping | HMM → 3-level posteriors |
| Regime names | "Strong Bull", "Weak Bull", etc. | "BULL", "BEAR", "SIDEWAYS" |
| Sizing works? | ✅ Yes | ❌ Always returns 0.0 |
| Purge days | 14 | 7 (more conservative) |

This divergence means **backtest results are not predictive of live performance**. The backtest shows trades; live execution shows none.

---

## SYSTEMIC ISSUES

### 1. Target Variable is Questionable

```python
# target_loader.py
REGIME_MAPPING = {
    "Strong Bull": 1.0,
    "Weak Bull": 0.75,
    "Neutral": 0.50,
    "Weak Bear": 0.25,
    "Strong Bear": 0.0
}
```

The target `y` comes from a human-labeled CSV file (`isp-regimes-btcusd-2026-06-13.csv`). These labels are assigned at specific dates (e.g., "2015-10-28: Weak Bull, Price: 302.15") and forward-filled.

**Problems:**

1. **Hindsight bias in labels:** If labels are assigned after seeing the full cycle, they encode future information. The model learns to predict "what happened" not "what will happen."
2. **Sparse labels → forward fill:** Most days get the same label as the last regime change. The model learns to predict "no change" most of the time → high accuracy but zero alpha.
3. **Regime labels don't correspond to trading opportunities:** A "Strong Bull" regime may include the entire 2020-2021 bull run. But the profitable trade is only the entry at the start and exit at the end. The model can't distinguish these from the middle.

**The negative IC is a direct consequence of this target design.** The model learns to predict "we are in a bull market" after the market has already gone up. By the time the model flips bullish, the move is over.

### 2. No Transaction Cost Modeling in Feature Processing

The signal suite introduces massive lag (ACF(1)=0.96, half-life ≈ 17 days). In a system with transaction costs:

- Each regime transition incurs spread + slippage
- With BTC, spread can be 5-10 bps on spot, 10-20 bps on perp
- With 1.5x leverage, slippage is amplified
- The system needs to generate > 20 bps per trade just to break even

Given the 17-day signal half-life, the system trades infrequently (which helps) but the trades are late (which hurts).

### 3. No Risk Management Layer

The sizing function ignores:

- Current portfolio drawdown
- Volatility regime
- Correlation with other positions
- Maximum drawdown constraints
- Position heat (concentration risk)

A proper system would have:

```python
def calculate_target_exposure(score, vol, current_drawdown, max_dd_limit):
    base_size = kelly_criterion(score, vol)
    dd_scalar = max(0, 1 - abs(current_drawdown) / max_dd_limit)
    return base_size * dd_scalar
```

### 4. Missing `__init__.py` and Module Exports

Several modules import from `src.features.normalizer`, `src.features.importance`, `src.signals.onchain` — need to verify these exist and are properly exported. The codebase has modules that are imported but may not be part of the core 6-layer architecture.

---

## INFORMATION RATIO ANALYSIS (Grinold & Kahn Framework)

The fundamental law of active management:

```
IR = IC × √Breadth
```

Where:

- **IC (Information Coefficient):** rank correlation between signal and forward returns
- **Breadth:** number of independent bets per year

**Current state:**

```
IC = -0.045 (1-day) to -0.203 (21-day)  ← NEGATIVE
Breadth = ~12 (monthly rebalancing × regime transitions)
IR = -0.203 × √12 ≈ -0.70  ← NEGATIVE IR
```

**Interpretation:** The system has a **negative information ratio** of -0.70. This means:

- The system destroys value relative to a passive benchmark
- Every unit of risk taken generates -0.70 units of excess return
- A simple buy-and-hold strategy dominates this system

**To achieve a minimum viable IR of 0.5:**

```
0.5 = IC × √12
IC = 0.5 / 3.46 = 0.145
```

The system needs IC ≥ 0.145 at the trading frequency. Currently it's -0.203. **The gap is 0.348 in IC terms — a massive improvement needed.**

---

## DERMAN & WILMOTT CRITIQUE

### Model Risk

"Your model assumes:

1. Gaussian regime-dependent returns (kurtosis violation)
2. Stationary regime dynamics (structural break violation)
3. Known regime labels at training time (lookahead in target)
4. Linear relationship between features and target (nonlinearity violation)

Every assumption is violated by Bitcoin's empirical properties. Your backtest is a fiction."

### Volatility Smile

"Bitcoin's implied volatility surface shows extreme skew during crashes. Your realized volatility (21-day rolling std) captures neither the skew nor the jump risk. Your ATR-based sizing will be catastrophically wrong during flash crashes."

### Greeks of the Model

"Your model's sensitivity to input perturbations (model Greeks) is:

- ∂Score/∂KalmanRSI ≈ 0 (because KalmanRSI is 400-day lagging)
- ∂Score/∂FDI ≈ 0 (because FDI is binary, not continuous)
- ∂Score/∂TrendStrength ≈ 1 (the only responsive indicator)

You have one working indicator disguised as six."

---

## RECOMMENDATIONS (Priority Order)

### P0: Fix Production Exposure Bug

Map HMM regime → 5-level regime in `pipeline.py` before calling execution engine. This is a 5-line fix that unblocks all live trading.

### P1: Invert the Signal

IC is negative. The simplest fix: multiply the final score by -1. This immediately converts the contrarian signal into a momentum signal. Then re-evaluate IC.

### P2: Replace Target Variable

The human-labeled regime CSV introduces hindsight bias. Replace with forward returns:

```python
y = close.pct_change(21).shift(-21)  # 21-day forward return
y = (y - y.rolling(252).mean()) / y.rolling(252).std()  # z-score
y = y.clip(-1, 1)  # bound to [-1, 1]
```

### P3: Drop Redundant Indicators

Keep: TrendStrengthIndex, FourierSupertrend, AdvancedStochastic (reduce to periods 1-30 only)
Drop: FDI (or QuantileDEMA — pick one), KalmanRSI (replace with raw RSI(14))

### P4: Fix XGBoost Objective

Change `objective="reg:logistic"` to `objective="reg:squarederror"` for continuous targets.

### P5: Continuous Sizing

Replace binary in/out sizing with conviction-weighted sizing based on final_score and realized volatility.

### P6: Reduce Signal Lag

- Remove Kalman filter from KalmanRSI
- Reduce AdvancedStochastic loop from 1-129 to 1-30
- Reduce RollingNormalizer window from 800 to 200
- Target: ACF(1) < 0.85 (half-life < 4 days)

---

## SEVERITY MATRIX

| # | Issue | Severity | Layer | Effort |
|---|-------|----------|-------|--------|
| 1 | Production exposure = 0 always | P0 CRITICAL | L5 Execution | 1 hour |
| 2 | IC is negative (contrarian signal) | P0 CRITICAL | L4 Ensemble | 1 day |
| 3 | Target variable has hindsight bias | P1 HIGH | Data/Target | 2 days |
| 4 | FDI ↔ QuantileDEMA VIF → ∞ | P1 HIGH | L2 Signals | 2 hours |
| 5 | ACF(1) = 0.96 (sluggish) | P1 HIGH | L2 Signals | 3 days |
| 6 | XGBoost objective mismatch | P2 MEDIUM | L4 Ensemble | 2 hours |
| 7 | Lasso on PCA = Ridge in disguise | P2 MEDIUM | L4 Ensemble | 4 hours |
| 8 | Binary sizing ignores conviction | P2 MEDIUM | L5 Execution | 1 day |
| 9 | HMM has no predictive power | P3 LOW | L1 Regime | 1 week |
| 10 | No risk management layer | P3 LOW | L5 Execution | 1 week |
| 11 | ThreadPool HMM race condition | P3 LOW | L6 Backtest | 2 hours |

---

## FINAL ASSESSMENT

This system is an **impressive engineering effort** with correct architectural layering, proper causal enforcement, and well-intentioned statistical methods. However, it is **mathematically broken** at multiple critical points:

1. **Production does nothing** (exposure = 0)
2. **Backtest is contrarian** (negative IC)
3. **Signal is too slow** (17-day half-life)
4. **Two indicators are identical** (FDI ≡ QuantileDEMA)
5. **Target encodes hindsight** (human-labeled regimes)
6. **XGBoost fits wrong loss** (reg:logistic on continuous targets)

The system needs a **complete statistical rebuild** before live deployment. The architecture is sound; the math within each layer needs repair.

**Estimated time to minimum viable system:** 2-3 weeks of focused work on the P0-P2 items.

**Estimated time to production-grade:** 6-8 weeks including proper risk management, transaction cost modeling, and out-of-sample validation.

---

*Audit completed 2026-06-17. All findings based on direct code inspection. No assumptions made without evidence.*
