## 1. Database Initialization

- [ ] 1.1 Create `src/execution/db.py` for SQLite connection management
- [ ] 1.2 Implement logic to initialize database at `database/lttd.db`
- [ ] 1.3 Configure database to use `PRAGMA journal_mode=WAL` on initialization
- [ ] 1.4 Write tests in `tests/execution/test_db_init.py` to verify database creation and WAL mode configuration

## 2. Schema Definition

- [ ] 2.1 Define SQL creation script for `daily_lttd` table with `CHECK` constraints on `regime` and `final_score`
- [ ] 2.2 Define SQL creation script for `indicator_scores` table with `CHECK` constraints on `score`
- [ ] 2.3 Define SQL creation script for `regime_transitions` table
- [ ] 2.4 Integrate schema execution into the initialization function in `src/execution/db.py`
- [ ] 2.5 Write tests in `tests/execution/test_schema.py` to verify schema constraints reject invalid bounds and regimes

## 3. Persistence Abstraction

- [ ] 3.1 Create `src/execution/persistence.py` to handle data insertion
- [ ] 3.2 Implement `upsert_daily_lttd` using `INSERT ... ON CONFLICT` for idempotency
- [ ] 3.3 Implement `upsert_indicator_scores` to persist Layer 2 signal components idempotently
- [ ] 3.4 Implement `log_regime_transition` to record state changes and probability metrics
- [ ] 3.5 Write tests in `tests/execution/test_persistence.py` to verify idempotent updates and explicit timestamp handling (BRK stamp alignment)
