## ADDED Requirements

### Requirement: Clean Repository Structure
The repository MUST contain only production code, production database, operational scripts, architecture documentation, and project configuration. All experimental, temporary, debug, and one-time output files MUST be removed from git tracking.

#### Scenario: Repository contains only production files after cleanup
- **WHEN** `git ls-files` is run after the cleanup change is applied
- **THEN** every tracked file belongs to one of these categories:
  - Production source code (`src/`, `tests/`, `backend/`, `frontend/`)
  - Production entry points (`backfill.py`, `backfill_all.py`, `backfill_db.py`, `run_pipeline.py`)
  - Operational scripts (`scripts/start_all.sh`, `scripts/performance_report.py`, `scripts/optimize_binary.py`, `scripts/init_db.ts`, `scripts/generate_chart.py`)
  - Architecture documentation (`pi_final_research_lttd_01.md`, `AGENTS.md`, `README.md`)
  - Reference data (`docs/`)
  - Project configuration (`.gitignore`, `requirements.txt`)
  - Change management (`openspec/`, `.agent/`)

#### Scenario: No temporary files are git-tracked
- **WHEN** `git ls-files | grep -E '(^tmp/|^fix_|^tmp_|^try_|^build_src|^scratch/|\.log$|^brk_cache|^random_search|^backtest_chart|^XGB_|^pi-statistic|^research_architecture|^0xbujang)'` is run
- **THEN** the output is empty (zero matches)

#### Scenario: Future temporary files are blocked by .gitignore
- **WHEN** a new file matching any of these patterns is created: `tmp/`, `*.log`, `brk_cache.json`, `*.csv` (root), `scratch/`, `.pi/`
- **THEN** `git status` does NOT show the file as untracked (blocked by `.gitignore`)

#### Scenario: Production tests still pass after cleanup
- **WHEN** `python -m pytest -xvs` is run after cleanup
- **THEN** all tests pass with zero failures

### Non-Goals
- Restructuring production code directories
- Moving or renaming production scripts
- Changing any pipeline logic or thresholds
- Archiving deleted files to a separate git branch
