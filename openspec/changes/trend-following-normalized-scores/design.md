## Context

Current LTTD system uses 5-layer architecture with 3-state HMM regime detection, 6 technical indicators outputting {-1, +1} signals, PCA/Lasso aggregation, and simple regime-based sizing. System achieves only 29.5% alignment with ISP target signals.

ISP target demonstrates clear trend-following pattern with 5 regimes (Strong Bull / Weak Bull / Neutral / Weak Bear / Strong Bear) and discrete buy/sell actions at regime transitions. Current architecture cannot represent graduated confidence or regime-aware threshold logic.

**Current State:**
```
Layer 1: 3-state HMM (BULL/BEAR/SIDEWAYS)
Layer 2: 6 indicators → {-1, +1}
Layer 3: PCA orthogonalization
Layer 4: L1-Lasso aggregation → [-1, +1]
Layer 5: Simple sizing (BULL→score, SIDEWAYS→0.5*score, BEAR→0)
```

**Target State:**
```
Layer 1: 5-state regime (Strong Bull / Weak Bull / Neutral / Weak Bear / Strong Bear)
Layer 2: N components → [0, 1] confidence with configurable thresholds
Layer 3: (removed — coherence replaces PCA)
Layer 4: Coherence engine (N/M components must agree)
Layer 5: Regime + Coherence → position sizing (50% / 100% / 0%)
```

## Goals / Non-Goals

**Goals:**
- Achieve ≥80% alignment with ISP signal timing (up from 29.5%)
- Every component outputs normalized confidence ∈ [0, 1]
- Each component has independently configurable buy/sell thresholds
- Components must achieve coherence (majority agreement) before trade execution
- 5-state regime detection matching ISP classifications
- Position sizing matches ISP pattern: 50% (Weak Bull entry) → 100% (Strong Bull add) → 50% (Weak Bull exit) → 0% (Neutral exit)

**Non-Goals:**
- Intraday trading (system operates on daily bars only)
- Short selling (long-only positioning)
- Multi-asset portfolio (BTC only)
- Real-time execution (daily rebalance at market close)
- Machine learning ensemble (keeping rule-based coherence for interpretability)

## Decisions

### Decision 1: 5-State Regime via Posterior Thresholding (not n_components=5)

**Choice:** Keep HMM n_components=3, add posterior probability thresholds to derive 5 states.

**Rationale:**
- HMM with n_components=5 on noisy BTC daily data causes overfitting (evidence: evaluasi-komponen-isp.md warns about stability)
- 3-state HMM is proven stable across 2015-2025 data
- Posterior probabilities provide natural confidence scores
- Threshold logic is transparent and tunable

**Implementation:**
```python
# From 3-state HMM posteriors
p_bull = posteriors["BULL"]
p_bear = posteriors["BEAR"]
p_neutral = posteriors["SIDEWAYS"]

# Derive 5-state classification
if p_bull > 0.7:
    regime = "Strong Bull"
elif p_bull > 0.4:
    regime = "Weak Bull"
elif p_bear > 0.7:
    regime = "Strong Bear"
elif p_bear > 0.4:
    regime = "Weak Bear"
else:
    regime = "Neutral"
```

**Alternatives Considered:**
- n_components=5 HMM: Rejected due to overfitting risk on noisy BTC data
- Separate classifiers per regime: Rejected due to complexity and data requirements

### Decision 2: Component Interface with [0, 1] Confidence Scores

**Choice:** New `TrendComponent` base class replacing `CausalFilter`, returning [0, 1] instead of {-1, +1}.

**Rationale:**
- [0, 1] enables threshold-based signal generation (score > buy_threshold → BUY)
- Regime-aware thresholds can be applied uniformly across all components
- Confidence scores enable weighted voting in coherence engine
- Backward compatible: existing indicators can be wrapped with normalization

**Implementation:**
```python
class TrendComponent(abc.ABC):
    def __init__(self, buy_threshold=0.6, sell_threshold=0.4, regime_adjusted=True):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.regime_adjusted = regime_adjusted
    
    @abc.abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """Return confidence score ∈ [0, 1]"""
        pass
    
    def signal(self, scores: pd.Series, regime: str) -> pd.Series:
        """Convert confidence → signal based on regime-adjusted thresholds"""
        buy_t, sell_t = self._adjust_thresholds(regime) if self.regime_adjusted else (self.buy_threshold, self.sell_threshold)
        signals = pd.Series(0.0, index=scores.index)
        signals[scores >= buy_t] = 1.0
        signals[scores <= sell_t] = -1.0
        return signals
```

**Alternatives Considered:**
- Keep {-1, +1} and add confidence separately: Rejected due to interface inconsistency
- Use probability (softmax) output: Rejected due to calibration complexity

### Decision 3: Coherence Engine with Majority Voting

**Choice:** Require ≥50%+1 components to agree before trade execution.

**Rationale:**
- Prevents single-component false signals
- ISP pattern shows coordinated regime transitions (multiple indicators agree)
- Majority voting is robust to outlier components
- Configurable: can upgrade to supermajority (75%) if needed

**Implementation:**
```python
class CoherenceEngine:
    def __init__(self, min_agreement=None, mode="majority"):
        self.min_agreement = min_agreement
        self.mode = mode  # "majority" | "supermajority" | "unanimous"
    
    def evaluate(self, component_signals: Dict[str, pd.Series], regime: str) -> pd.DataFrame:
        n = len(component_signals)
        required = self.min_agreement or (n // 2 + 1)
        
        buy_votes = sum((s == 1.0).astype(int) for s in component_signals.values())
        sell_votes = sum((s == -1.0).astype(int) for s in component_signals.values())
        
        coherence = pd.Series(0.0, index=buy_votes.index)
        coherence[buy_votes >= required] = 1.0
        coherence[sell_votes >= required] = -1.0
        
        return pd.DataFrame({
            "coherence_signal": coherence,
            "confidence": coherence.abs() * (buy_votes.where(coherence == 1, sell_votes) / n),
        })
```

**Alternatives Considered:**
- Weighted voting by component accuracy: Rejected due to complexity (weights need WFO training)
- Unanimous agreement: Rejected due to overly conservative signal generation
- No coherence (current approach): Rejected due to 29.5% alignment failure

### Decision 4: Regime-Aware Threshold Adjustment

**Choice:** Adjust component thresholds based on current regime to match ISP trading pattern.

**Rationale:**
- ISP buys at Weak Bull (early entry) — lower buy threshold in bull regimes
- ISP sells at Weak Bull/Neutral (exit on weakening) — lower sell threshold in neutral/bear
- Prevents over-trading in sideways markets
- Matches institutional trend-following behavior

**Implementation:**
```python
REGIME_ADJUSTMENTS = {
    "Strong Bull":  (-0.1, +0.1),  # buy easier, sell harder
    "Weak Bull":    (0.0, 0.0),    # normal
    "Neutral":      (+0.1, -0.1),  # buy harder, sell easier
    "Weak Bear":    (+0.2, -0.2),  # buy much harder, sell much easier
    "Strong Bear":  (+0.3, -0.3),  # buy hardest, sell easiest
}
```

**Alternatives Considered:**
- Fixed thresholds: Rejected due to poor ISP alignment
- ML-learned thresholds: Rejected due to overfitting risk

### Decision 5: ISP Position Sizing Logic

**Choice:** Hardcode position sizing to match ISP pattern exactly.

**Rationale:**
- ISP uses discrete 50% / 100% / 0% sizing (not continuous)
- Simplifies execution and reduces slippage
- Matches institutional position management
- Easier to validate against ISP target

**Implementation:**
```python
def determine_position(regime: str, coherence_signal: float, current_position: float) -> float:
    if coherence_signal == 1.0:  # BUY signal
        if regime in ("Weak Bull", "Strong Bull"):
            return 0.5 if current_position < 0.5 else 1.0
    elif coherence_signal == -1.0:  # SELL signal
        if regime == "Weak Bull":
            return 0.5 if current_position > 0.5 else 0.0
        elif regime in ("Neutral", "Weak Bear", "Strong Bear"):
            return 0.0
    return current_position  # HOLD
```

**Alternatives Considered:**
- Continuous Kelly sizing: Rejected due to complexity and overfitting risk
- Volatility-adjusted sizing: Deferred to future iteration

## Risks / Trade-offs

**[Risk] Component score normalization may lose indicator-specific information**
→ Mitigation: Keep raw indicator values available for debugging; normalization is only for threshold comparison

**[Risk] Majority voting may still allow false signals if 3/6 components are wrong**
→ Mitigation: Start with majority, monitor ISP alignment; upgrade to supermajority if needed

**[Risk] 5-state regime classification may be unstable at regime boundaries**
→ Mitigation: Add hysteresis (require regime to persist N days before action); tune posterior thresholds via WFO

**[Risk] Hardcoded ISP sizing may not generalize to future market conditions**
→ Mitigation: Validated on 2015-2025 data; monitor live performance; defer dynamic sizing to future iteration

**[Risk] Existing indicators may not produce well-calibrated [0, 1] scores**
→ Mitigation: Use rolling min-max normalization per indicator; validate score distributions in tests

## Migration Plan

1. **Phase 1: New Interface** — Create `TrendComponent` base class alongside existing `CausalFilter`
2. **Phase 2: Indicator Migration** — Convert 6 indicators to new interface, validate [0, 1] output
3. **Phase 3: Regime Upgrade** — Add 5-state classification to existing HMM
4. **Phase 4: Coherence Engine** — Implement and unit test voting logic
5. **Phase 5: Execution Rewrite** — Replace sizing logic with regime + coherence mapping
6. **Phase 6: Integration** — Rewire pipeline, run full backtest against ISP
7. **Phase 7: Validation** — Compare backtest signals with ISP CSV, measure alignment

**Rollback:** Keep old `CausalFilter` and PCA/Lasso ensemble available until Phase 6 validation passes.

## Open Questions

1. **Component selection**: Which 6 indicators best capture ISP regime transitions? Need IC analysis.
2. **Threshold tuning**: What are optimal default buy/sell thresholds per component? Need WFO.
3. **Coherence mode**: Should we start with majority or supermajority? Need ablation study.
4. **Posterior thresholds**: What p_bull/p_bear thresholds best match ISP 5-state classifications? Need grid search.
5. **Hysteresis period**: How many days must regime persist before action? Need sensitivity analysis.
