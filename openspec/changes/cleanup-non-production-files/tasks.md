## 1. Remove `tmp/` directory (100 tracked files)

- [x] 1.1 Run `git rm -r tmp/` to remove all 100 tracked files from the tmp directory
- [x] 1.2 Remove the `tmp/` directory from filesystem if it still exists after git rm

## 2. Remove root-level throwaway scripts

- [x] 2.1 Run `git rm fix_all.py fix_builder_test.py fix_engine_test.py fix_target_test.py fix_tests.py fix_xgb_test.py`
- [x] 2.2 Run `git rm tmp_explore_composite.py tmp_explore_tops.py tmp_explore_zscore.py`
- [x] 2.3 Run `git rm try_project.py build_src.py`

## 3. Remove optimization artifacts and cache files

- [x] 3.1 Run `git rm backtest_chart.html brk_cache.json random_search_results.csv`
- [x] 3.2 Delete untracked log files: `rm -f optimize.log optimize2.log optimize_lasso.log` (these match `*.log` in .gitignore so may already be untracked — verify first)

## 4. Remove research/audit markdown files from root

- [x] 4.1 Run `git rm XGB_MEMORY.md XGB_PLAN.md pi-statistic-quant-audit.md`
- [x] 4.2 Run `git rm research_architecture_audit_ds_20260617.md research_architecture_audit_quant_20260617.md research_architecture_audit_synthesis_20260617.md research_architecture_gap_analysis_20260617.md`

## 5. Remove legacy Pine Script and .pi directory

- [x] 5.1 Run `git rm 0xbujang-lttd.pinescript`
- [x] 5.2 Remove `.pi/` directory: `rm -rf .pi/` (check if tracked first; if tracked, use `git rm -r .pi/`)

## 6. Remove one-time scripts and audit outputs from `scripts/`

- [x] 6.1 Run `git rm -r scripts/audit_charts/`
- [x] 6.2 Run `git rm scripts/audit_data_quality_report.json scripts/audit_quant_rigor_report.json`
- [x] 6.3 Run `git rm scripts/analysis_binary.py scripts/analysis_buckets.py scripts/analysis_conviction.py scripts/analysis_voldrag.py`
- [x] 6.4 Run `git rm scripts/analyze_csv.py scripts/analyze_thresholds.py scripts/evaluate_csv.py scripts/evaluate_rules.py`
- [x] 6.5 Run `git rm scripts/audit_data_quality.py scripts/audit_isp_targets.py scripts/audit_quant_rigor.py scripts/component_audit.py scripts/indicator_statistical_audit.py`
- [x] 6.6 Run `git rm scripts/optimize.py scripts/optimize_de.py scripts/random_search_pipeline.py scripts/print_trades.py scripts/train_rules.py`

## 7. Remove cache files from `database/`

- [x] 7.1 Run `git rm database/onchain_cache.csv` (if tracked; verify with `git ls-files database/onchain_cache.csv`)

## 8. Update `.gitignore` to prevent re-accumulation

- [x] 8.1 Add `tmp/` entry (distinct from `scratch/` which is already ignored)
- [x] 8.2 Add `brk_cache.json` entry
- [x] 8.3 Add `*.csv` root-level exclusion (with `!docs/**/*.csv` exception to keep ISP data)
- [x] 8.4 Add `*.html` root-level exclusion
- [x] 8.5 Add `.pi/` entry
- [x] 8.6 Add `database/*.csv` entry for cache files
- [x] 8.7 Verify `*.log` and `scratch/` are already covered (they are)

## 9. Update AGENTS.md reference to deleted Pine Script

- [x] 9.1 Update the `0xbujang-lttd.pinescript` reference in AGENTS.md Gold Standard section to note the file was deleted (recoverable from git history)

## 10. Validate

- [x] 10.1 Run `python -m pytest -xvs` to confirm all production tests pass
- [x] 10.2 Run `git ls-files | grep -E '(^tmp/|^fix_|^tmp_|^try_|^build_src|^scratch/|\.log$|^brk_cache|^random_search|^backtest_chart|^XGB_|^pi-statistic|^research_architecture|^0xbujang)'` and verify zero matches
- [x] 10.3 Run `git status` to verify clean working tree with only the planned deletions staged
- [ ] 10.4 Commit with message: `chore(repo): remove non-production files and update .gitignore`
