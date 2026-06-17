# Data Science Architecture Audit — CRISP-DM Rigor Review

**Date:** 2026-06-17  
**Auditor:** lz-data-science-core  
**Scope:** Full LTTD system — data ingestion, feature engineering, ensemble modeling, execution  
**Lens:** Senior data scientist who has shipped ML models at scale  
**Framework:** CRISP-DM  

---

## Executive Summary

**Verdict: The system has fundamental data science flaws that make its current output unreliable.** The model is not learning meaningful patterns. The 52.58% hit rate, negative IC, and ACF(1)=0.96 are not edge effects — they are symptoms of a system that is architecturally broken at multiple layers.

This audit identifies **4 BLOCKERs**, **7 CRITICAL warnings**, and **5 recommended fixes** ranked by impact. The root causes, in order of severity:

1. **Target variable is a forward-filled constant** — the model is predicting the regime of a date 50–382 days in the past
2. **On-chain features are never fed to the ML model** — they only modify HMM posteriors
3. **HMM regime labels don't match sizing labels** — exposure is always 0.0
4. **6 technical indicators with 37 ISP labels for XGBoost** — catastrophic overfitting by construction

---

## CRISP-DM Phase 1: Business Understanding

### Rating: ⚠️ WARNING

**Problem Definition:** The system aims to predict BTC long-term trend direction (120–350 day horizon) and size positions accordingly. The target is a 5-class ordinal label: `{Strong Bear: 0.0, Weak Bear: 0.25, Neutral: 0.50, Weak Bull: 0.75, Strong Bull: 1.0}`.

**What the system actually decides:** Whether to hold BTC at 0x, 1x, or 1.5x leverage based on the regime classification.

**Issues Found:**

**B1. Misaligned Problem Framing** — The system tries to predict the *regime at a point in time*, but the ISP labels mark *transition dates*. Between transition dates, the regime is constant. The model is asked to predict a label that hasn't changed in 73 days (mean gap between ISP transitions). This is not a classification problem — it's a *change-point detection* problem disguised as regression.

Evidence: `isp-regimes-btcusd-2026-06-13.csv` has 51 labels over 3,670 days (2015-10-28 to 2025-11-12). Mean gap = 73 days. Median = 40 days. Max gap = 382 days (2016-05-28 to 2017-06-14 — a full year of a single regime).

**B2. No Defined Business Metric** — There is no Sharpe ratio target, no maximum drawdown constraint, no risk budget. The sizing function (`sizing.py`) uses hard-coded thresholds (`0.6 → Weak Bull`, `0.2 → Neutral`) without any calibration against historical risk-adjusted returns.

---

## CRISP-DM Phase 2: Data Understanding

### Rating: 🔴 FAIL

### 2.1 Target Variable Quality

**C1. FORWARD-FILL CREATES FAKE SAMPLES (BLOCKER)**

The target loader (`target_loader.py:33-44`) creates a daily continuous target by forward-filling 51 sparse ISP labels across 2,483+ dates. This means:

- Date 2019-04-02: ISP label = Strong Bull (1.0)
- Date 2019-04-03 through 2019-05-19: **all labeled 1.0** (48 fake samples)
- Date 2019-05-20: ISP label = Weak Bull (0.75)

The model trains on 2,483 samples, but only **51 are ground truth**. The remaining 2,432 are interpolated constants. This creates:

1. **Massive class imbalance by duration** — Bull regimes dominate (2019-2021 bull market fills ~800 days at 0.75–1.0)
2. **Serial correlation in targets** — the target at day t is identical to day t-1 for 73 days on average
3. **False confidence** — the model appears to have high accuracy because it's predicting the same constant value for months

Evidence: `target_loader.py:44` — `filled_series = df['RegimeIntensity'].reindex(combined_idx).ffill()`. The `REGIME_MAPPING` converts 5 labels to numeric, then forward-fills across the entire daily index.

**C2. ISP LABELS ARE SUBJECTIVE AND SPARSE**

50 hand-labeled transitions over 10 years of BTC data. That's roughly 5 labels per year. The inter-annotator agreement is unknown. The labeling criteria are not formalized.

Key concern: The ISP labels start at 2015-10-28, but the OHLCV data starts at 2017-08-17. That means **8 ISP labels** (2015-2017) have no matching OHLCV data. These labels are only useful if the on-chain data (which starts 2012) covers them, but the system only joins OHLCV + on-chain via `point_in_time_join` — so those 8 pre-2017 labels are effectively orphaned.

Evidence: ISP CSV first label = 2015-10-28, OHLCV pipeline fetches from Binance starting 2015-01-01 but Binance BTCUSDT only has data from 2017-08-17. `exchange_adapter.py:62` — `start_time=datetime(2015, 1, 1, ...)` but Binance API returns empty for pre-2017 BTCUSDT.

### 2.2 Feature Data Quality

**C3. ON-CHAIN FEATURES NOT IN ML FEATURE MATRIX (BLOCKER)**

The `FeatureMatrixBuilder.build_matrix()` (`builder.py:37-57`) computes only 6 technical indicators from OHLCV:

- FDI, AdvancedStochastic, KalmanRSI, FourierSupertrend, TrendStrengthIndex, QuantileDEMA

On-chain metrics (STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit) are fetched, merged into `df_merged`, and used ONLY for:

1. HMM posterior overrides (`filter.py` — `apply_onchain_overrides`)
2. Telemetry logging

They are **never added to the feature matrix** that feeds the ML ensemble.

Evidence: `pipeline.py:119` — `feature_matrix = builder.build_matrix(df_merged)`. `builder.py:37-57` — `build_matrix` only calls `self.fdi.compute(data)`, `self.advanced_stochastic.compute(data)`, etc. — all OHLCV-only indicators. `pipeline.py:146` — `X_train = feature_matrix.loc[train_idx_purged]` — only the 6-column matrix goes to the model.

**C4. HMM REGIME NOT USED AS ML FEATURE**

The HMM regime classification (Layer 1) produces `BULL/BEAR/SIDEWAYS` labels and posteriors, but these are never fed to the ML model as features. The ensemble sees only the 6 PCA-transformed technical indicators. The HMM regime is used only for:

1. Final regime determination (`pipeline.py:140` — `final_regime_hmm = max(overridden_posteriors, ...)`)
2. Sizing decisions via `calculate_target_exposure`

This means the ML model has no knowledge of the detected regime when making predictions.

### 2.3 Data Leakage Assessment

**C5. PURGING STRATEGY IS INADEQUATE**

The pipeline purges only 7 days before execution (`pipeline.py:143` — `train_idx_purged = train_idx[train_idx < t - pd.Timedelta(days=7)]`). But:

1. **Forward-filled targets leak** — the target at day t-7 is identical to the target at day t (forward fill). Purging 7 days removes the *same label* that exists at t, creating a false sense of separation.
2. **Technical indicators with 350-day lookback** — indicators like FourierSupertrend with `dynamic_lookback` up to 350 days are computed on the full `df_merged` (not just training data). When `processor.fit(X_train, y_train)` runs, `X_train` contains indicator values that were computed using data from up to 350 days before each training bar — including data that's within the purge window.

Evidence: `pipeline.py:117-119` — indicators are built on the FULL `df_merged`, then sliced to `train_idx_purged`. The indicator computation itself is causal per bar, but the feature matrix is built on the entire history, not incrementally.

**C6. WFO PURGE OF 14 DAYS IN BACKTEST RUNNER vs 7 DAYS IN DAILY PIPELINE**

The backtest runner (`runner.py:155`) uses `purge_days=14`, while the daily pipeline uses 7 days. This inconsistency means backtest results don't match production behavior.

Evidence: `runner.py:155` — `iterator = WFOIterator(purge_days=14)`. `pipeline.py:143` — `train_idx_purged = train_idx[train_idx < t - pd.Timedelta(days=7)]`.

---

## CRISP-DM Phase 3: Data Preparation

### Rating: 🔴 FAIL

### 3.1 Train/Test Split

**C7. NO TEMPORAL SPLIT VALIDATION IN DAILY PIPELINE**

The daily pipeline (`pipeline.py:103-108`) uses a fixed 3-year (1095 day) trailing window for training. There is no holdout set, no temporal cross-validation, and no performance tracking across windows. The model is fit, predicts one day, and is discarded.

Evidence: `pipeline.py:103-108` — `train_idx = df_merged.index[(df_merged.index >= t - pd.Timedelta(days=1095)) & (df_merged.index < t)]`

### 3.2 Effective Sample Size

**C8. EFFECTIVE N IS ~37, NOT 2,483**

After accounting for:

- 51 ISP labels (only 37 fall within DB range 2018-05-01 to 2025-02-15)
- Forward-fill creates correlated samples (effective N ≈ number of regime transitions)
- Purging removes adjacent samples
- OU half-life clamping to [120, 350] reduces variability

The effective independent sample size for model training is approximately **37 regime transitions** (the number of ISP labels that overlap with the DB date range). This is far too small for XGBoost with 300 estimators and max_depth=4.

Evidence: 37 ISP labels overlap with DB dates. ACF(1)=0.96 confirms massive serial correlation. Effective N ≈ N × (1 - ACF(1)) / (1 + ACF(1)) ≈ 2483 × 0.04 / 1.96 ≈ **51 independent observations** — and this is optimistic because the ACF is computed on a constant series for long stretches.

### 3.3 Label Noise

**C9. LABEL DISTRIBUTION IS HEAVILY IMBALANCED**

ISP label distribution (within DB range):

- Strong Bull: 5 labels
- Weak Bull: 10 labels
- Neutral: 10 labels
- Weak Bear: 8 labels
- Strong Bear: 4 labels

After forward-filling, the *temporal* distribution is dominated by Bull regimes (2019-2021 and 2023-2024 bull markets contribute hundreds of days at 0.75–1.0). The model is trained to predict "Bull" most of the time because the bull market lasts longer.

Evidence: DB regime distribution: SIDEWAYS=1241, BULL=979, BEAR=263. But ISP labels say the market was Bull (Weak+Strong) for 15 of 37 labels (40.5%). The forward-fill creates a bull-heavy training set.

---

## CRISP-DM Phase 4: Modeling

### Rating: 🔴 FAIL

### 4.1 Model Selection

**C10. XGBoost ON 6 FEATURES WITH 37 EFFECTIVE SAMPLES (BLOCKER)**

The XGBoost ensemble (`xgboost_model.py`) uses:

- `n_estimators=300`
- `max_depth=4`
- `subsample=0.7`
- `colsample_bytree=0.7`

With only 6 input features (PCA-transformed from 6 indicators) and ~37 effective samples, this model has:

- 300 trees × 4 depth × minimum 1 sample per leaf = capacity for thousands of parameters
- 37 effective samples → extreme overfitting
- The model memorizes the training set and produces high-confidence predictions on in-sample data

Evidence: `xgboost_model.py:23-35` — `n_estimators=300, max_depth=4` with 6 features. `run_daily()` fits the model on ~1095 training bars but only 37 are independent.

**C11. SCALE_POS_WEIGHT IS MEANINGLESS WITH CONTINUOUS TARGET**

`xgboost_model.py:27` — `scale_pos_weight = num_neg / max(1, num_pos)` where the threshold is `y >= 0.5`. Since the target is a continuous [0, 1] intensity (not binary), this weight is arbitrary. A value of 0.5 doesn't correspond to any meaningful class boundary.

**C12. REG:LOGISTIC OBJECTIVE ON REGRESSION TARGET**

`xgboost_model.py:31` — `objective="reg:logistic"` applies a sigmoid transformation to the output. This is designed for binary classification, not regression on continuous [0, 1] values. The sigmoid squashes extreme predictions toward 0 and 1, which is correct for probabilities but inappropriate for a continuous intensity target that can legitimately be 0.0 or 1.0.

### 4.2 Hyperparameter Tuning

**C13. NO HYPERPARAMETER TUNING**

All hyperparameters are hard-coded:

- XGBoost: `n_estimators=300, learning_rate=0.03, max_depth=4` (`xgboost_model.py:23-35`)
- PCA: `variance_threshold=0.85` (`pca.py:12`)
- VIF: `vif_threshold=10.0` (`vif.py`)
- Lasso: `alpha=0.01` (`model.py:20`)
- HMM: `n_components=3, n_iter=100` (`hmm.py:32`)

No grid search, no Bayesian optimization, no walk-forward hyperparameter tuning. The WFO infrastructure exists but doesn't tune hyperparameters — it only refits the same model on rolling windows.

### 4.3 Overfitting Evidence

**C14. ACF(1)=0.96 CONFIRMS MODEL IS PREDICTING PERSISTENCE, NOT SIGNAL**

The final_score autocorrelation at lag 1 is 0.96. This means the model's output today is 96% identical to yesterday's output. This is the signature of a model that has learned:

1. The forward-filled target (which is constant for 73 days on average)
2. The PCA-transformed indicators (which are smooth, slowly-moving)

The model is not predicting regime transitions — it's predicting the current regime, which it could do by simply looking at yesterday's label.

Evidence: ACF(1)=0.96, ACF(5)=0.876, ACF(10)=0.821, ACF(50)=0.520.

**C15. NEGATIVE IC AT ALL HORIZONS**

The Information Coefficient (correlation between predicted score and forward returns) is negative at all horizons. This means the model's predictions are *inversely* related to future returns — buying when the model says "bull" actually leads to losses.

Evidence: Known issue #2 — "Negative IC at all horizons."

### 4.4 Model Architecture Issues

**C16. HMM DOES NOT SEPARATE RETURNS (BLOCKER)**

The HMM is trained on log returns + realized volatility, but the t-test p>0.46 means the three states (BULL/BEAR/SIDEWAYS) do not have statistically different mean returns. The HMM is classifying states based on volatility clustering, not directional returns.

Evidence: Known issue #3 — "Regime detection doesn't separate returns (t-test p>0.46)."

`hmm.py:87-95` — state labeling uses `means_[:, 0]` (log returns), but if the HMM hasn't separated returns, the BULL/BEAR/SIDEWAYS labels are arbitrary.

**C17. VIF → ∞ FOR FDI & QUANTILEDEMA**

FDI and QuantileDEMA have infinite VIF, meaning they are perfectly correlated with other indicators. The VIF pruning should drop one of them, but the current threshold of 10.0 may not handle ∞ gracefully.

Evidence: Known issue #4 — "FDI & QuantileDEMA VIF → ∞."

`vif.py:18-20` — constant-zero std gets `vifs[col] = float("inf")`, but the pruning loop (`vif.py:63-85`) correctly handles this by including `inf > 10.0` in `high_vif_cols`.

**C18. OU HALF-LIFE CLAMPED TO [120, 350] REDUCES ALL INDICATORS TO SIMILAR LOOKBACKS**

`ou_calibration.py:33` — `return max(120.0, min(350.0, hl))`. All indicators share the same `dynamic_lookback` value, which is a single scalar clamped to [120, 350]. This means:

1. The dynamic lookback doesn't actually vary across indicators
2. The clamping range is so narrow that the "dynamic" aspect adds minimal value
3. All 6 indicators use approximately the same lookback window, which contradicts the goal of diversity

Evidence: `pipeline.py:114` — `dynamic_lookback = estimate_ou_halflife(log_prices.loc[train_idx], ...)` returns a single float. `builder.py:20` — all 6 indicators receive the same `dynamic_lookback` scalar.

---

## CRISP-DM Phase 5: Evaluation

### Rating: 🔴 FAIL

### 5.1 Evaluation Metrics

**C19. NO WALK-FORWARD OUT-OF-SAMPLE METRICS**

The daily pipeline produces a single-day prediction with no backtest metrics. The backtest runner exists but:

1. Uses a different purge window (14 days vs 7 days)
2. Doesn't report IC, hit rate, or regime-specific metrics
3. The reported hit rate (52.58%) is computed on the full dataset, not walk-forward

**C20. NO BASELINE COMPARISON**

There is no comparison against:

- **Buy-and-hold** (the simplest BTC strategy)
- **Moving average crossover** (the simplest trend-following strategy)
- **Random classifier** (50% hit rate for binary, 20% for 5-class)

The 52.58% hit rate is meaningless without knowing the baseline. For a 2-class problem, 50% is random. For a 5-class problem, 20% is random. But the system uses a continuous target, so "hit rate" definition matters.

### 5.2 Regime-Specific Analysis

**C21. HMM REGIME LABELS DON'T MATCH ISP LABELS**

When comparing HMM-generated regimes to ISP labels at overlapping dates:

- **Agreement: 35.1%** (13 out of 37 matching dates)
- The HMM says BULL when ISP says Weak Bear (2019-07-03: HMM=BULL, ISP=Weak Bear)
- The HMM says SIDEWAYS when ISP says Strong Bull (2020-07-24: HMM=SIDEWAYS, ISP=Strong Bull)

Evidence: Manual overlap check shows massive disagreement. The HMM classifies based on returns+volatility, while ISP labels are based on a different (unknown) methodology.

**C22. TARGET EXPOSURE IS ALWAYS 0.0 (BLOCKER)**

The sizing function (`sizing.py`) expects regime labels in the format `"Strong Bull"`, `"Weak Bull"`, `"Neutral"`, `"Weak Bear"`, `"Strong Bear"`. But the HMM produces labels `"BULL"`, `"BEAR"`, `"SIDEWAYS"`. Since none of the HMM labels match the sizing function's expected values, `calculate_target_exposure()` returns 0.0 for every date.

Evidence:

```
calculate_target_exposure(0.5, "BULL") → 0.0
calculate_target_exposure(0.5, "BEAR") → 0.0
calculate_target_exposure(0.5, "SIDEWAYS") → 0.0
```

DB confirms: 2,483 rows, all with `target_exposure = 0.0`.

**C23. BACKTEST REGIME MAPPING IS INCONSISTENT**

The backtest runner (`runner.py:177-185`) maps the final_score to 5-state regimes using thresholds:

```python
if score >= 0.6: "Strong Bull"
elif score >= 0.2: "Weak Bull"
elif score >= -0.2: "Neutral"
elif score >= -0.6: "Weak Bear"
else: "Strong Bear"
```

But the daily pipeline (`pipeline.py:140`) uses the HMM regime directly:

```python
final_regime = final_regime_hmm  # BULL/BEAR/SIDEWAYS
```

This means backtest and production produce different regime labels for the same data.

---

## CRISP-DM Phase 6: Deployment

### Rating: ⚠️ WARNING

### 6.1 Production Readiness

**D1. NO MODEL MONITORING**

There is no:

- Prediction distribution tracking
- Feature drift detection
- Performance degradation alerts
- Shadow mode comparison

The `execution/persistence.py` saves daily records to SQLite, but no monitoring dashboard or alerting system exists.

**D2. NO RETRAINING TRIGGER**

The model is retrained from scratch every day (pipeline fits on 1095-day window). There is no:

- Performance decay detection
- Automatic retraining schedule
- Model versioning
- A/B testing framework

**D3. FRESHNESS VALIDATION IS GOOD**

`BRKIngestionService.validate_freshness()` correctly checks that `feed.stamp >= current_date - timedelta(days=1)`. This prevents using stale on-chain data.

Evidence: `brk_ingestion_service.py:46-57` — proper freshness validation with `DataStaleException`.

**D4. CAUSAL FILTER BASE CLASS IS WELL-DESIGNED**

The `CausalFilter` base class (`signals/base.py`) enforces strict causality with `_resolve_lookback()` clamping to [120, 350]. This is architecturally sound.

### 6.2 Data Pipeline Reliability

**D5. EXCHANGE ADAPTER HAS RETRY LOGIC**

`exchange_adapter.py:42-50` — exponential backoff with 5 retries. This is good practice.

**D6. MISSING DATA HANDLING USES FFILL**

`pipeline.py:42-49` — forward-fill for missing OHLCV data. This is standard practice for crypto markets (weekend gaps, exchange outages).

---

## Detailed Issue Inventory

### BLOCKERS (Must fix before any meaningful results)

| # | Issue | Location | Impact |
|---|---|---|---|
| C1 | Forward-filled targets create 2,432 fake training samples from 51 labels | `target_loader.py:33-44` | Model trains on constant values, not transitions |
| C3 | On-chain features never enter ML model | `builder.py:37-57`, `pipeline.py:119` | 4 on-chain metrics fetched but unused in ensemble |
| C10 | XGBoost overfitting: 300 trees on 37 effective samples | `xgboost_model.py:23-35` | Model memorizes training data |
| C22 | target_exposure always 0.0 (HMM labels don't match sizing) | `sizing.py` + `hmm.py` | System never takes a position |

### CRITICAL Warnings (Must address for model to learn anything)

| # | Issue | Location | Impact |
|---|---|---|---|
| B1 | Problem framed as regression, should be change-point detection | Architecture | Wrong objective function |
| C5 | 7-day purge insufficient for 350-day lookback indicators | `pipeline.py:143` | Temporal leakage |
| C6 | Backtest purge (14d) ≠ production purge (7d) | `runner.py:155` vs `pipeline.py:143` | Results don't transfer |
| C8 | Effective N ≈ 37, far below XGBoost requirements | Statistical | Extreme overfitting |
| C12 | `reg:logistic` on continuous regression target | `xgboost_model.py:31` | Wrong loss function |
| C16 | HMM doesn't separate returns (p>0.46) | `hmm.py` | Regime labels are noise |
| C18 | OU half-life clamped to [120, 350] — all indicators get similar lookback | `ou_calibration.py:33` | False diversity |

### Recommended Fixes (Priority Order)

| # | Fix | Effort | Impact |
|---|---|---|---|
| 1 | **Replace forward-fill target with forward return prediction** — predict 30/60/90-day forward log return, discretize into classes | Medium | Fixes C1, eliminates fake samples |
| 2 | **Add on-chain features to feature matrix** — append STH-MVRV, STH-NUPL, STH-SOPR, STH-SupplyInProfit as columns in `build_matrix()` | Low | Fixes C3, uses 4 metrics already fetched |
| 3 | **Map HMM regimes to sizing labels** — add `{"BULL": "Weak Bull", "BEAR": "Weak Bear", "SIDEWAYS": "Neutral"}` mapping before `calculate_target_exposure` | Low | Fixes C22, enables actual trading |
| 4 | **Replace XGBoost with simpler model** — use L1-Lasso (`MLConsensusEngine`) which already exists and is more appropriate for small N | Low | Fixes C10, C12 |
| 5 | **Add HMM regime as feature** — include `p_bull`, `p_bear`, `p_sideways` in the feature matrix | Low | Fixes C4, gives ML model regime context |

---

## ISP Label Analysis

### Label Quality Assessment

| Metric | Value | Assessment |
|---|---|---|
| Total labels | 51 | **Insufficient** for ML. Minimum recommended: 200+ transitions |
| Labels in DB range | 37 | Even fewer usable labels |
| Mean gap between labels | 73 days | Regime is constant for ~2.5 months on average |
| Max gap | 382 days | Full year without a transition |
| Label distribution | 14 Weak Bull, 13 Neutral, 11 Weak Bear, 7 Strong Bull, 6 Strong Bear | Reasonably balanced across classes |
| Date range | 2015-10-28 to 2025-11-12 | 10 years of data |

### Label Noise Estimate

Without inter-annotator agreement data, we can estimate noise by checking internal consistency:

- 2019-05-20 (Weak Bull, $7,964) → 2019-06-28 (Neutral, $12,327) — price *rose* 55% but regime weakened. This could be correct (top detection) or noise.
- 2020-03-13 (Strong Bear, $5,628) → 2020-03-26 (Neutral, $6,747) — 13-day recovery from COVID crash labeled correctly.
- 2025-04-21 (Weak Bull, $87,117) → 2025-08-18 (Neutral, $116,263) — price *rose* 34% but regime weakened. Suspicious.

Rough noise estimate: **15–25%** of labels may be debatable. With only 51 labels, even 5 mislabeled transitions (10%) significantly degrades model training.

---

## Feature Matrix Analysis

### Current: 6 Technical Indicators

| Indicator | Type | Lookback Dependency |
|---|---|---|
| FDI | Fractal Dimension | Dynamic (120-350) |
| AdvancedStochastic | Momentum oscillator | Dynamic (120-350) |
| KalmanRSI | Filtered momentum | Dynamic (120-350) |
| FourierSupertrend | Spectral trend | Dynamic (120-350) |
| TrendStrengthIndex | Trend magnitude | Dynamic (120-350) |
| QuantileDEMA | Quantile trend | Dynamic (120-350) |

**Problem:** All 6 indicators measure the same underlying signal (momentum/trend direction via different smoothing methods). VIF → ∞ for FDI and QuantileDEMA confirms this. PCA reduces dimensionality but doesn't create new information.

### Missing: 4 On-Chain Metrics (Already Fetched)

| Metric | Signal Type | Value |
|---|---|---|
| STH-MVRV | Valuation | Cycle top/bottom detection |
| STH-NUPL | Sentiment | Euphoria/capitulation |
| STH-SOPR | Behavior | Spend profit ratio |
| STH-SupplyInProfit | Distribution | Profit-taking pressure |

These metrics have **different information content** from price-based indicators. Adding them would increase feature diversity and potentially improve IC.

### Missing: HMM Posteriors

| Feature | Signal Type | Value |
|---|---|---|
| p_bull | Regime probability | Directional conviction |
| p_bear | Regime probability | Downside conviction |
| p_sideways | Regime probability | Uncertainty level |

These are already computed but not fed to the ML model.

---

## On-Chain Override Analysis

The `apply_onchain_overrides` function (`filter.py:4-36`) implements two hard rules:

1. STH-MVRV > 2.0 → BULL posterior forced to 0.0
2. STH-NUPL > 0.75 → BULL posterior capped at 0.50

**Issue:** These are the only uses of on-chain data in the entire system. The 4 on-chain metrics (fetched from BRK API with 1,200-day lookback) are reduced to two binary threshold checks. This wastes the information content of the on-chain data.

**Better approach:** Feed raw on-chain values as features to the ML model, letting it learn the non-linear relationships.

---

## OU Half-Life Calibration Assessment

**What it does:** Estimates the mean-reversion half-life of BTC log prices using an AR(1) regression. The result (clamped to [120, 350]) is passed as `dynamic_lookback` to all 6 indicators.

**Does it add value?** Marginal. The clamping range [120, 350] means:

- If estimated HL < 120 → all indicators use 120
- If estimated HL > 350 → all indicators use 350
- The actual variation across time is likely small (BTC's HL has been >300 days since 2020)

**Net assessment:** The OU calibration adds complexity without proportionate benefit. A fixed lookback of 250 days would produce nearly identical results for the post-2020 period.

---

## Effective Sample Size Analysis

| Factor | Reduction |
|---|---|
| Raw samples | 2,483 days |
| Forward-fill correlation | ÷ ~73 (mean gap) → ~34 independent regimes |
| ISP labels in DB range | 37 labels |
| Purging (7 days) | Removes ~7 bars per transition → ~30 effective samples |
| OU half-life similarity | All indicators use similar lookback → reduced feature diversity |
| **Effective N for ML** | **~30-37** |

Rules of thumb for sample size:

- **Logistic regression:** Minimum 10 events per predictor. With 6 features: need 60 events. We have ~30. **FAILS.**
- **XGBoost:** No formal minimum, but 300 trees × depth 4 = massive overfitting risk. **FAILS.**
- **L1-Lasso:** More robust to small N due to regularization. **BORDERLINE.**

---

## Summary Ratings

| CRISP-DM Phase | Rating | Key Finding |
|---|---|---|
| 1. Business Understanding | ⚠️ WARNING | Problem framed as regression, should be change-point detection |
| 2. Data Understanding | 🔴 FAIL | Forward-filled targets, on-chain features unused, 37 effective labels |
| 3. Data Preparation | 🔴 FAIL | Inadequate purging, no temporal validation, label imbalance |
| 4. Modeling | 🔴 FAIL | XGBoost overfitting, wrong loss function, no tuning, ACF=0.96 |
| 5. Evaluation | 🔴 FAIL | No walk-forward metrics, no baselines, 35% HMM-ISP agreement |
| 6. Deployment | ⚠️ WARNING | No monitoring, no retraining triggers, but causal pipeline is sound |

---

## Appendix: Code Evidence Locations

| Finding | File | Lines |
|---|---|---|
| Forward-fill target | `src/data/target_loader.py` | 33-44 |
| Missing on-chain in feature matrix | `src/features/builder.py` | 37-57 |
| HMM regime mismatch in sizing | `src/execution/sizing.py` | 1-20 |
| XGBoost overfitting params | `src/ensemble/xgboost_model.py` | 23-35 |
| 7-day purge (vs 14 in backtest) | `src/pipeline.py` | 143 |
| OU half-life clamping | `src/features/ou_calibration.py` | 33 |
| On-chain override (only use of on-chain) | `src/regime/filter.py` | 4-36 |
| ACF(1)=0.96 | DB analysis | N/A |
| ISP label gaps | `docs/isps/isp-regimes-btcusd-2026-06-13.csv` | All rows |

---

*End of audit. The system requires fundamental restructuring of the target variable and feature matrix before any model training produces meaningful results.*
