## Why

Current system outputs directional signals ∈ {-1, +1} and aggregates via PCA/Lasso. ISP target uses **5 regimes** (Strong Bull → Weak Bull → Neutral → Weak Bear → Strong Bear) with **discrete buy/sell actions at regime transitions**. System achieves only 29.5% alignment with ISP timing (evaluasi-komponen-isp.md). Root cause: current architecture cannot represent graduated confidence levels or regime-aware threshold logic.

ISP trading pattern is clear trend-following:
- **BUY** at Weak Bull transition (early entry, 50% equity)
- **BUY** at Strong Bull (add position, 100% equity)
- **SELL** at Weak Bull (partial exit as regime weakens)
- **SELL** at Neutral (full exit)

Current [-1, +1] signals cannot encode "how confident is this component that we're entering a bull regime" — only direction. Normalized [0, 1] scores enable regime-aware threshold tuning where each component independently decides when to vote BUY/SELL based on its confidence level.

## What Changes

- **BREAKING**: Replace `CausalFilter.compute()` return type from `{-1, +1}` to `[0, 1]` confidence scores
- New `TrendComponent` base class with configurable `buy_threshold` and `sell_threshold` per component
- New `CoherenceEngine` requiring N/M components to agree before trade execution
- Upgrade regime detection from 3-state HMM to 5-state (Strong Bull / Weak Bull / Neutral / Weak Bear / Strong Bear) via posterior probability thresholding
- New `RegimeAwareThresholds` that adjust component thresholds based on current regime
- Rewrite execution engine to match ISP position sizing logic (50% / 100% / 0%)
- New backtest validation against ISP signals CSV for exact match verification

## Capabilities

### New Capabilities
- `trend-component-interface`: Base class for all signal components outputting [0, 1] confidence with configurable buy/sell thresholds
- `coherence-engine`: Voting mechanism requiring component agreement before trade execution
- `five-state-regime-detection`: 5-state regime classification via HMM posterior probability thresholding
- `regime-aware-thresholds`: Dynamic threshold adjustment based on current regime state
- `isp-target-matching`: Backtest validation ensuring system replicates ISP signal timing and position sizing

### Modified Capabilities
- `ensemble-aggregation`: Change from PCA-weighted [-1, +1] aggregation to coherence-based [0, 1] voting
- `regime-weighted-sizing`: Replace 3-state sizing logic with 5-state regime + coherence signal mapping
- `hmm-regime-classification`: Upgrade from 3-state to 5-state via posterior thresholding (not n_components change)
- `walk-forward-optimization`: Update target variable from next-day return sign to regime transition label

## Impact

**Architecture Layers Affected:**
- Layer 2 (Signal Engine): All 6 existing indicators must adopt new `TrendComponent` interface
- Layer 4 (Ensemble): Replace PCA/Lasso aggregation with `CoherenceEngine`
- Layer 5 (Execution): Complete rewrite of sizing logic for 5 regimes

**Files to Modify:**
- `src/signals/base.py` — New `TrendComponent` abstract class
- `src/signals/*.py` — All 6 indicator implementations (KalmanRSI, FDI, QuantileDEMA, FourierSupertrend, AdvancedStochastic, TrendStrength)
- `src/ensemble/*.py` — New coherence engine, deprecate PCA/Lasso ensemble
- `src/execution/*.py` — Rewrite sizing for 5 regimes
- `src/regime/hmm.py` — Add 5-state classification via posterior thresholds
- `src/pipeline.py` — Rewire layer connections

**Dependencies:** No new external dependencies. Uses existing hmmlearn, pandas, numpy.

**Backtest Impact:**
- Expected improvement: 29.5% → 80%+ ISP alignment (primary success metric)
- Sharpe ratio: Current ~1.2 → Target ~1.8 (fewer false signals from coherence requirement)
- Max drawdown: Current ~35% → Target ~25% (regime-aware sizing reduces exposure in Neutral/Bear)
- Trade frequency: Reduced ~40% (coherence filter eliminates weak signals)
