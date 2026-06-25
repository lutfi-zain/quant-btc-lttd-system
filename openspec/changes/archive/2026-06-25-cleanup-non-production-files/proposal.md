## Why

The repository has accumulated ~100+ temporary/scratch files that were useful during research and development but are not part of the production system. These include:

- **100 files in `tmp/`** — one-off debug scripts, optimization experiments, ichimoku research, inspect/evaluate scripts, HTML reports, and optimization result JSONs (~17 MB total)
- **11 root-level throwaway files** — `fix_*.py`, `tmp_explore_*.py`, `try_project.py`, `build_src.py`
- **Optimization artifacts** — `optimize.log`, `optimize2.log`, `optimize_lasso.log`, `random_search_results.csv`, `backtest_chart.html` (5.4 MB)
- **One-time audit outputs** — `scripts/audit_charts/` (14 PNGs), `scripts/audit_*_report.json`
- **Research markdown artifacts** — `XGB_MEMORY.md`, `XGB_PLAN.md`, `pi-statistic-quant-audit.md`, 4× `research_architecture_audit_*.md` files
- **Cache files** — `brk_cache.json` (320 KB), `database/onchain_cache.csv` (340 KB)
- **Legacy Pine Script** — `0xbujang-lttd.pinescript` (100 KB) — referenced only as historical baseline per AGENTS.md, not production code
- **Legacy `.pi/` directory** — old Pi runtime settings/prompts

This clutter makes navigating the codebase harder, inflates the repo size, and risks confusion between production and experimental code.

**No statistical/backtest impact** — this is a housekeeping change that removes only non-production files. No indicators, ensemble logic, sizing thresholds, or pipeline code is touched.

## What Changes

**Remove** all non-production files from git tracking (via `git rm`) and from the filesystem. Specifically:

1. Delete entire `tmp/` directory (100 tracked files)
2. Delete root-level throwaway scripts: `fix_*.py`, `tmp_explore_*.py`, `try_project.py`, `build_src.py`
3. Delete optimization log/output files: `optimize*.log`, `random_search_results.csv`, `backtest_chart.html`
4. Delete audit outputs: `scripts/audit_charts/`, `scripts/audit_*_report.json`
5. Delete one-time research docs: `XGB_MEMORY.md`, `XGB_PLAN.md`, `pi-statistic-quant-audit.md`, `research_architecture_audit_*.md`, `research_architecture_gap_*.md`
6. Delete cache files: `brk_cache.json`, `database/onchain_cache.csv`
7. Delete legacy reference: `0xbujang-lttd.pinescript`
8. Delete legacy directory: `.pi/`
9. Delete one-time scripts from `scripts/` that are not ongoing production utilities
10. Update `.gitignore` to prevent re-accumulation of these file categories

**Keep** (production code + DB):
- `src/` — all production Python layers
- `tests/` — all test suites
- `backend/` — Hono API
- `frontend/` — React dashboard
- `database/lttd.db` (+ WAL/SHM) — production database
- `scripts/start_all.sh`, `scripts/performance_report.py`, `scripts/optimize_binary.py`, `scripts/init_db.ts` — essential operational scripts
- `backfill.py`, `backfill_all.py`, `backfill_db.py`, `run_pipeline.py` — production entry points
- `requirements.txt`, `AGENTS.md`, `README.md`, `.gitignore` — project config
- `pi_final_research_lttd_01.md` — architecture blueprint (source of truth per AGENTS.md)
- `openspec/` — change management
- `.agent/` — agent configuration
- `docs/` — retain ISP reference data and indicator audit report

## Capabilities

### New Capabilities
- `repo-hygiene`: Enforce clean repository structure with updated `.gitignore` rules to prevent future accumulation of temp/scratch/cache files

### Modified Capabilities
_None — no production behavior changes._

## Impact

- **Repository size**: Significant reduction (~25 MB of tracked files removed)
- **No code changes**: Zero modifications to any `src/`, `tests/`, `backend/`, `frontend/` files
- **No backtest impact**: CAGR, Sharpe, max DD unchanged — no pipeline code is touched
- **No new dependencies**: None
- **Architecture layers affected**: None (Layer 1–6 untouched)
- **Risk**: Very low — only deleting files that are not imported or referenced by production code
