## 1. Execution Engine Refactoring

- [x] 1.1 Modify `calculate_target_exposure` in `src/execution/sizing.py` to return `1.0` if `final_score >= 0.5`, else `0.0`.
- [x] 1.2 Remove the legacy 5-state categorical if/else blocks from `calculate_target_exposure` while keeping the `regime` argument in the function signature for backward compatibility.

## 2. Validation & Testing

- [x] 2.1 Update or add unit tests for `calculate_target_exposure` to verify the exact 0.5 threshold logic (e.g. `0.5 -> 1.0`, `0.499 -> 0.0`).
- [x] 2.2 Run full test suite `python -m pytest --cov` to ensure no upstream callers (e.g. `BacktestRunner`) are broken by the simplified logic.
