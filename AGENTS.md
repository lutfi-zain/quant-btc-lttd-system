# AGENTS.md

**Repository:** `quant-btc-lttd-system`  
**Domain:** Quantitative Bitcoin Long-Term Trend Direction (LTTD) Trading System

This file is the authoritative guide for AI coding agents working in this repository. It defines the quantitative architecture, code style rules, statistical testing requirements, and hard constraints every change must satisfy.

---

## Commands

```bash
# Fast validation (fail fast)
python -m pytest -xvs

# Full validation with coverage
python -m pytest --cov

# Install dependencies
python -m pip install -r requirements.txt

# Backtest run (when implemented)
python -m src.backtest.runner --walk-forward --start 2017-01-01 --end 2025-01-01
```

Run all tests and confirm they pass before finalizing any change.

---

## Project Context & Business Domain (DDD)

**Ubiquitous Language — strictly enforce these terms. Do NOT hallucinate synonyms.**

| Term | Definition |
|---|---|
| **LTTD** | Long-Term Trend Direction — the macro directional bias of BTC (Bull/Bear/Sideways) over a 120–350 day horizon |
| **Regime** | Market state classification: `BULL`, `BEAR`, or `SIDEWAYS`, detected by the HMM layer on log returns + volatility |
| **OU Half-Life** | Ornstein-Uhlenbeck mean-reversion half-life; Bitcoin's structural reversion speed (pre-2017: 40–80 days; post-2020: 300+ days) |
| **Indicator Score** | Binary directional signal from a single indicator, ∈ {-1, +1} |
| **Final Score** | Weighted ensemble output over all indicator scores, range [-1.0, +1.0] |
| **Technical Indicator** | Price-derived signal computed from OHLCV data (e.g., Kalman RSI, FDI, Supertrend variants) |
| **On-Chain Metric** | Blockchain-behavioral metric: STH-MVRV, STH-SOPR, NUPL, Supply In Profit (pulled live from Glassnode API) |
| **STH (Short-Term Holder)** | BTC addresses that held coins for fewer than 155 days — key cohort for MVRV/SOPR signals |
| **LTH (Long-Term Holder)** | BTC addresses that held coins for more than 155 days — capitulation/conviction baseline |
| **PCA Orthogonalization** | Principal Component Analysis applied to the indicator matrix to eliminate multicollinearity before aggregation |
| **Ensemble Model** | The aggregation layer — one of: PCA-weighted voting, L1-Lasso Logistic Regression, or HMM+XGBoost |
| **Causal Filter** | A real-time filter that only reads `source[i]` for i≥0 (past bars only); NEVER a centered/symmetric window |
| **Lookahead Bias** | Use of future data points in any indicator calculation — **this invalidates all backtest results** |
| **Walk-Forward Optimization (WFO)** | Rolling train/validate/test pipeline: train 3yr → validate 6mo → test 6mo; slide window forward |
| **CPCV** | Combinatorial Purged Cross-Validation — purge training bars adjacent to the test window to prevent leakage |
| **Pratt's Measure** | Relative importance metric: `dⱼ = βⱼ · rⱼ / R²`, used to prune redundant indicators |
| **VIF** | Variance Inflation Factor — indicator pairs with VIF > 10 MUST be orthogonalized or one must be dropped |
| **HMM** | Hidden Markov Model, 3-state, trained on daily log returns + realized volatility for regime classification |

Ensure all variable names, function signatures, database columns, API response keys, and comments strictly adhere to this ubiquitous language.

---

## Architecture Boundaries (Progressive Disclosure)

The system is organized into **6 strictly layered modules**. Do not mix concerns across layers.

```
LAYER 1: REGIME DETECTION        (src/regime/)
        ↓ [infers Bull/Bear/Sideways]
LAYER 2: SIGNAL ENGINE           (src/signals/)
        ↓ [outputs causal indicator scores ∈ {-1, +1}]
LAYER 3: FEATURE PROCESSING      (src/features/)
        ↓ [PCA orthogonalization, standardization, VIF pruning]
LAYER 4: ENSEMBLE AGGREGATION    (src/ensemble/)
        ↓ [outputs Final Score ∈ [-1.0, +1.0]]
LAYER 5: EXECUTION ENGINE        (src/execution/)
        ↓ [writes daily_lttd rows to SQLite]
LAYER 6: PRESENTATION            (backend/ + frontend/)
        [Hono API serves SQLite → React SPA visualizes]
```

**Layer rules:**
- Layer N may ONLY import from Layer N-1 or lower. No circular imports.
- `src/regime/` has ZERO dependency on price indicators. HMM only sees returns + volatility.
- `src/signals/` MUST implement a `CausalFilter` base class. No symmetric windows.
- `src/features/` owns all multicollinearity detection. Run VIF check before adding any new indicator.
- `src/ensemble/` applies WFO. No single static fit on full history.
- `src/execution/` receives ONLY the `Final Score` + regime state. No raw indicators.
- `backend/` reads ONLY from SQLite (`lttd.db`). Never imports Python src directly.
- `frontend/` fetches ONLY from `backend/` REST endpoints. No direct DB or Python calls.

**Gold Standard Reference Files:**

> Agents: Read these before creating new components. They define the expected code quality and patterns.

- **Architecture Blueprint:** [`pi_final_research_lttd_01.md`](./pi_final_research_lttd_01.md) — mathematical proofs, layer design, indicator audit decisions. **Primary source of truth for ALL design decisions.**
- **Legacy Reference (Do NOT copy patterns):** [`0xbujang-lttd.pinescript`](./0xbujang-lttd.pinescript) — audit completed; contains critical flaws (SGF lookahead, hardcoded arrays, multicollinearity). Referenced only as a historical baseline for indicator naming.

---

## Security & Compliance Guardrails

### HARD PROHIBITIONS (will cause invalid backtests or live losses):

- ❌ **Never hardcode on-chain data as static arrays.** The Pine Script pattern (`F1_data = array.from("2024-01-01|1", ...)`) bypasses real-time latency and API revisions. All on-chain metrics MUST be fetched live via Glassnode API (or equivalent).
- ❌ **Never use symmetric/centered filters in real-time execution.** Savitzky-Golay with a centered window references future bars. Any filter using `source[i]` for negative `i` (or future offsets in Python: `series[t+k]`) introduces lookahead bias. Use `CausalFilter` base class only.
- ❌ **Never stack raw correlated indicators.** Never average 12 RSI/DEMA variants and call it "multi-indicator." Always run VIF analysis first. Drop or orthogonalize indicators with VIF > 10.
- ❌ **Never fit the ensemble on the full historical dataset.** Always use Walk-Forward Optimization. Static fits overfit to the market regime that no longer exists.
- ❌ **Never assume on-chain data timestamp = event timestamp.** BRK data is derived from on-chain settled state; always use the `stamp` field from the API response as the `data_as_of` value, not `datetime.now()`.
- ❌ **Never use Pine Script `calc_on_every_tick = true` patterns in Python.** All indicator computations run on closed/confirmed bars (`barstate.isconfirmed` equivalent = using `shift(1)` in pandas to avoid leakage).

### REQUIRED PRACTICES:
- ✅ Always run `pytest --cov` before marking any task complete
- ✅ All new indicators must pass a `test_no_lookahead()` unit test that verifies the indicator value at time `t` does not change when future bars `t+1..t+N` are appended
- ✅ All on-chain metrics must be fetched via the BRK API (`https://bitview.space/api/series/{name}/day`) or `brk-client`. Use a typed `BRKFeed` interface (not raw `requests` dict access)
- ✅ Use the correct BRK series names: `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit` (NOT Glassnode names)
- ✅ Log every `Regime` transition with timestamp, posterior probability, and triggering metrics

---

## Git & Workflow Conventions

- **Branching Strategy:** `feature/LTTD-{issue-number}-{short-desc}` (e.g., `feature/LTTD-001-regime-hmm`)
- **Pushing Rules:** Never `git push --force` or `--force-with-lease`. Always `git pull --rebase` first. Resolve conflicts locally, then push normally.
- **Commit Format:** Conventional Commits with domain prefix:
  - `feat(regime): add 3-state HMM training pipeline`
  - `feat(signals): implement causal Kalman RSI`
  - `fix(ensemble): correct PCA component selection threshold`
  - `data(onchain): update Glassnode API client for MVRV endpoint`
  - `backtest(wfo): implement walk-forward optimization runner`
  - `refactor(features): replace VIF threshold from 10 to 8`
- **PR Rules:** Every PR must include a backtest delta summary (Sharpe before/after, max drawdown change)

---

## Dependencies & Environment

- **Primary Language:** Python 3.11+
- **Package Manager (Python):** `pip` (use `python -m pip install`; do NOT use pip3)
- **Package Manager (JS/TS):** `bun` (use `bun install`, `bun run`; do NOT use npm or pnpm)
- **Core Data Stack:** `pandas`, `numpy`, `scipy`
- **ML Stack:** `scikit-learn`, `hmmlearn`, `xgboost`
- **Signal Processing:** `scipy.signal` for causal-only filtering; NO `scipy.signal.savgol_filter` with centered windows
- **On-Chain Data:** [BRK (Bitcoin Research Kit)](https://github.com/bitcoinresearchkit/brk) via `brk-client` (`pip install brk-client`). Hosted free at `https://bitview.space`. **No API key required.**
- **Persistence:** SQLite in WAL mode (`database/lttd.db`) — same pattern as `quant-btc-valuation-system`
- **API Server:** Hono v4 running on Bun runtime (`backend/index.ts`)
- **Frontend:** React 18 + TypeScript, bundled with Vite (`frontend/`)
- **Charts:** TradingView Lightweight Charts (`bun add lightweight-charts`)
- **Backtesting:** `vectorbt` or `backtrader` (to be decided in design artifact)
- **Testing (Python):** `pytest` + `pytest-cov`
- **Testing (TS):** Bun test runner (`bun test`)
- **Config secrets:** Load exchange API keys from env vars. NEVER hardcode. NEVER commit `.env`.
- **Environment Variables Required:**
  ```
  EXCHANGE_API_KEY=...         # Optional: live execution
  BTC_DATA_SOURCE=...          # e.g., "binance", "coinbase"
  DB_PATH=...                  # Optional: override default database/lttd.db path
  ```
  > BRK/bitview.space requires NO authentication — do not add env vars for it.

---

## OpenSpec Workflow

This repository uses **OpenSpec** for structured change management. Always follow the artifact flow before implementing.

```bash
# Check current active changes
openspec list

# Propose a new change (fast path)
/opsx:propose

# Or with full artifact control
/opsx:new <change-name>
/opsx:ff               # creates proposal → specs → design → tasks
/opsx:apply            # implement tasks
/opsx:verify           # validate implementation vs artifacts
/opsx:archive          # merge deltas + archive
```

**Artifact rules:**
- Proposals MUST state the mathematical/statistical motivation for the change
- Specs MUST include concrete Given/When/Then scenarios with measurable acceptance criteria
- Design MUST reference layer boundaries from the architecture above
- Tasks MUST be small enough to complete in one session

**Active changes folder:** `openspec/changes/`  
**Source-of-truth specs folder:** `openspec/specs/`

---

## Historical Session Learnings

*Critical findings from the initial research session (2026-06-07). Read these before implementing any indicator or aggregation logic.*

- **[2026-06-07] SGF Lookahead Bug:** Pine Script Indicator 12 (Savitzky-Golay Flow Bands) appears to use `source[0]..source[15]` (historical access only), but the coefficient loop structure is broken — it produces near-symmetric polynomial fit that mimics zero-lag behavior in TradingView backtests. In real-time, the coefficients yield a heavily lagged asymmetric polynomial predictor. **Do not port this indicator.** Replace with adaptive Fourier-based causal filter.

- **[2026-06-07] Static Array On-Chain Silence:** The Pine Script's `F1_data`..`F4_data` arrays hardcode historical on-chain signals. Any bar after the last array date yields `score = 0`. In Python with BRK, always assert freshness: `assert brk_feed.stamp >= current_date - timedelta(days=1)` before computing the ensemble. BRK's `/api/series/{name}/day/latest` endpoint returns the most recent confirmed value — check the `stamp` field in the response.

- **[2026-06-07] OU Half-Life is Epoch-Dependent:** Don't fix the trend lookback at 200 days. Bitcoin's OU half-life shifted from 40–80 days (pre-2017) to 300+ days (post-2020). Run empirical OU fitting quarterly and adjust the LTTD epoch window dynamically. Current estimated window: **120–350 days** depending on HMM regime.

- **[2026-06-07] Glassnode Feature Discovery Finding:** Optimal BTC uptrend detection context windows are **800–1,200 days** — far longer than conventional 50/200-day periods. When computing rolling statistics on on-chain metrics (MVRV, NUPL), use a minimum lookback of 800 days.

- **[2026-06-07] On-Chain Lead-Lag Asymmetry:** MVRV and NUPL **lead** price at cycle tops by 3–14 days but **lag** or coincide at capitulation bottoms. Do not use on-chain metrics as execution triggers. Use as **regime filters** only (scale down max exposure when NUPL > 0.75 or STH-MVRV > 2.0).

- **[2026-06-07] Multicollinearity in 12 Technical Indicators:** The legacy script stacks 12 indicators all measuring the same underlying signal (momentum/trend direction via different MA variants). VIF analysis would reveal 9 of 12 have VIF > 10. Simple averaging inflates model confidence and causes synchronized failure during regime shifts. After PCA orthogonalization, the first 3 components capture >85% of variance — the remaining 9 indicators add noise, not signal.
