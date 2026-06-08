## 1. Database Initialization

- [x] 1.1 Create `src/execution/db.py` for SQLite connection management
- [x] 1.2 Implement logic to initialize database at `database/lttd.db`
- [x] 1.3 Configure database to use `PRAGMA journal_mode=WAL` on initialization
- [x] 1.4 Write tests in `tests/execution/test_db_init.py` to verify database creation and WAL mode configuration

## 2. Schema Definition

- [x] 2.1 Define SQL creation script for `daily_lttd` table with `CHECK` constraints on `regime` and `final_score`
- [x] 2.2 Define SQL creation script for `indicator_scores` table with `CHECK` constraints on `score`
- [x] 2.3 Define SQL creation script for `regime_transitions` table
- [x] 2.4 Integrate schema execution into the initialization function in `src/execution/db.py`
- [x] 2.5 Write tests in `tests/execution/test_schema.py` to verify schema constraints reject invalid bounds and regimes

## 3. Persistence Abstraction

- [x] 3.1 Create `src/execution/persistence.py` to handle data insertion
- [x] 3.2 Implement `upsert_daily_lttd` using `INSERT ... ON CONFLICT` for idempotency
- [x] 3.3 Implement `upsert_indicator_scores` to persist Layer 2 signal components idempotently
- [x] 3.4 Implement `log_regime_transition` to record state changes and probability metrics
- [x] 3.5 Write tests in `tests/execution/test_persistence.py` to verify idempotent updates and explicit timestamp handling (BRK stamp alignment)
