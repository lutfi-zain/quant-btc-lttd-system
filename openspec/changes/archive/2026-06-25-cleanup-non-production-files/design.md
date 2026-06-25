## Context

The repository currently tracks ~150+ files that are not part of the production system. These accumulated during the research, development, and optimization phases. The production system is well-defined across 6 layers (`src/`, `tests/`, `backend/`, `frontend/`, `database/`) plus a handful of entry-point scripts. Everything else is experimental detritus.

## Goals / Non-Goals

**Goals:**
- Remove all non-production files from git tracking and filesystem
- Update `.gitignore` to prevent future accumulation
- Achieve a clean, navigable repository where every tracked file has a clear production purpose
- Preserve `pi_final_research_lttd_01.md` as the architecture blueprint (per AGENTS.md)
- Preserve `docs/` reference data (ISP CSVs, indicator audit report)

**Non-Goals:**
- Refactoring or restructuring production code
- Moving scripts between directories
- Changing any logic in `src/`, `tests/`, `backend/`, or `frontend/`
- Archiving files to a separate branch (they remain in git history)
- Removing `openspec/` or `.agent/` configuration

## Decisions

### D1: Delete vs Archive
**Decision:** Delete files (via `git rm`), do not archive to a separate branch.
**Rationale:** Git history preserves all deleted content. Anyone can `git show HEAD~1:tmp/file.py` to recover any file. A separate archive branch adds maintenance overhead with no practical benefit.

### D2: Which `scripts/` to keep
**Decision:** Keep only scripts that are referenced in AGENTS.md or serve ongoing production/operational needs:
- `scripts/start_all.sh` — canonical startup
- `scripts/performance_report.py` — production performance reporting
- `scripts/optimize_binary.py` — threshold optimizer (referenced by AGENTS.md for sizing calibration)
- `scripts/init_db.ts` — database initialization
- `scripts/generate_chart.py` — chart generation utility

Delete all other scripts (one-time audits, analysis scripts, CSV evaluators, threshold analyzers, etc.)

### D3: Keep `pi_final_research_lttd_01.md`
**Decision:** Keep this file. It is the **architecture blueprint** and explicit source of truth per AGENTS.md. Delete all other research/audit markdown files from root.

### D4: Keep `docs/` directory
**Decision:** Retain `docs/indicator_audit_report.md` and `docs/isps/` (ISP reference CSVs). These are ongoing reference materials, not one-time outputs.

### D5: `.gitignore` additions
**Decision:** Add explicit entries to prevent future accumulation:
- `tmp/` — already partially covered by `scratch/`, but `tmp/` was tracked
- `*.html` in root (e.g., `backtest_chart.html`)
- `brk_cache.json`
- `*.csv` in root
- `optimize*.log`
- `.pi/`

### D6: Keep `0xbujang-lttd.pinescript` reference in AGENTS.md only
**Decision:** Delete the actual file. The AGENTS.md already documents it as "Legacy Reference (Do NOT copy patterns)" and notes it "contains critical flaws." The reference in AGENTS.md text is sufficient context — the 100KB file adds no production value. Update AGENTS.md to note the file was removed (available in git history).

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accidentally delete production file | Low | High | Explicit keep-list verified against imports; `git rm` only, recoverable from history |
| Developer needs a deleted script | Low | Low | All files remain in git history; `git show` or `git checkout` can recover |
| Future temp files accumulate again | Medium | Low | `.gitignore` updated to block common patterns |
| AGENTS.md reference to deleted Pine Script breaks | None | None | Update AGENTS.md to note file removed, available in git history |
