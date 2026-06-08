## 1. Setup and Directory Structure

- [x] 1.1 Create `src/signals/` directory and `__init__.py`
- [x] 1.2 Create `tests/signals/` directory and `__init__.py`

## 2. CausalFilter Base Class

- [x] 2.1 Create `src/signals/base.py`
- [x] 2.2 Define `CausalFilter` inheriting from `abc.ABC`
- [x] 2.3 Implement abstract method `compute(self, data: pd.DataFrame) -> pd.Series`
- [x] 2.4 Add comprehensive docstrings enforcing causality rules and {-1, +1} output constraints

## 3. Lookahead Verification Utility

- [x] 3.1 Create `tests/signals/utils.py`
- [x] 3.2 Implement `test_no_lookahead(indicator: CausalFilter, data: pd.DataFrame, t_index: int)`
- [x] 3.3 Within `test_no_lookahead`, compute indicator on data truncated at `t_index`
- [x] 3.4 Within `test_no_lookahead`, compute indicator on full extended data
- [x] 3.5 Assert that the output at `t_index` is strictly identical in both computations

## 4. Unit Testing and Mock Validation

- [x] 4.1 Create `tests/signals/test_base.py`
- [x] 4.2 Create a `DummyCausalIndicator` that adheres to the causal constraints (e.g., simple past moving average)
- [x] 4.3 Create a `DummyLookaheadIndicator` that intentionally uses future data (e.g., using `shift(-1)` or a centered window)
- [x] 4.4 Write a test asserting that `test_no_lookahead` passes for `DummyCausalIndicator`
- [x] 4.5 Write a test asserting that `test_no_lookahead` raises an `AssertionError` for `DummyLookaheadIndicator`
- [x] 4.6 Run `python -m pytest --cov` to verify coverage and correctness
