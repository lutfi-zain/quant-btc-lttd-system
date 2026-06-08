## 1. Setup and Directory Structure

- [ ] 1.1 Create `src/signals/` directory and `__init__.py`
- [ ] 1.2 Create `tests/signals/` directory and `__init__.py`

## 2. CausalFilter Base Class

- [ ] 2.1 Create `src/signals/base.py`
- [ ] 2.2 Define `CausalFilter` inheriting from `abc.ABC`
- [ ] 2.3 Implement abstract method `compute(self, data: pd.DataFrame) -> pd.Series`
- [ ] 2.4 Add comprehensive docstrings enforcing causality rules and {-1, +1} output constraints

## 3. Lookahead Verification Utility

- [ ] 3.1 Create `tests/signals/utils.py`
- [ ] 3.2 Implement `test_no_lookahead(indicator: CausalFilter, data: pd.DataFrame, t_index: int)`
- [ ] 3.3 Within `test_no_lookahead`, compute indicator on data truncated at `t_index`
- [ ] 3.4 Within `test_no_lookahead`, compute indicator on full extended data
- [ ] 3.5 Assert that the output at `t_index` is strictly identical in both computations

## 4. Unit Testing and Mock Validation

- [ ] 4.1 Create `tests/signals/test_base.py`
- [ ] 4.2 Create a `DummyCausalIndicator` that adheres to the causal constraints (e.g., simple past moving average)
- [ ] 4.3 Create a `DummyLookaheadIndicator` that intentionally uses future data (e.g., using `shift(-1)` or a centered window)
- [ ] 4.4 Write a test asserting that `test_no_lookahead` passes for `DummyCausalIndicator`
- [ ] 4.5 Write a test asserting that `test_no_lookahead` raises an `AssertionError` for `DummyLookaheadIndicator`
- [ ] 4.6 Run `python -m pytest --cov` to verify coverage and correctness
