## 1. Persistence Layer (SQLite WAL)

- [ ] 1.1 Create `src/execution/database.py` with a SQLite connection factory.
- [ ] 1.2 Configure database connections to strictly enforce `PRAGMA journal_mode=WAL;` and appropriate connection timeouts to prevent Layer 6 blocking.
- [ ] 1.3 Implement schema initialization to create the `daily_lttd` table with columns: `data_as_of` (BRK stamp), `final_score`, `regime`, `target_exposure`, and `posterior_prob`.
- [ ] 1.4 Write unit tests to verify WAL mode activation, table schema creation, and database initialization logic.

## 2. Target Sizing Logic

- [ ] 2.1 Create `src/execution/sizing.py` with a function to calculate target BTC exposure based on `Final Score` and `Regime`.
- [ ] 2.2 Implement BULL regime sizing rule: target exposure scales directly with positive `Final Score` up to 1.0.
- [ ] 2.3 Implement SIDEWAYS regime sizing rule: target exposure scales with `Final Score` but is hard-capped at 0.5.
- [ ] 2.4 Implement BEAR regime sizing rule: target exposure is strictly forced to 0.0.
- [ ] 2.5 Write `test_no_lookahead` and sizing boundary unit tests to verify scaling behavior and pure causal computation.

## 3. Transition Telemetry and Logging

- [ ] 3.1 Create `src/execution/logger.py` containing a `RegimeTransitionLogger` class.
- [ ] 3.2 Implement logic to track `previous_regime` vs `current_regime` and detect regime shifts.
- [ ] 3.3 Implement structured log formatting (JSON or domain-prefixed text) to emit exactly: `Regime`, `BRK Stamp`, `P(Bull)`, `P(Bear)`, `P(Sideways)`, `Log Return`, and `Realized Volatility`.
- [ ] 3.4 Write unit tests ensuring logs are only emitted during a state transition and contain all requisite data.

## 4. Execution Engine Integration

- [ ] 4.1 Create `src/execution/engine.py` defining the `ExecutionEngine` class.
- [ ] 4.2 Implement the `run()` pipeline method that accepts Layer 4 outputs (`Final Score`, `Regime`, posteriors, etc.).
- [ ] 4.3 Coordinate the pipeline to compute target exposure via `sizing.py`, evaluate regime transitions via `logger.py`, and persist the final daily record to the `daily_lttd` table.
- [ ] 4.4 Write an integration test simulating a multi-day walk-forward scenario to verify correct pipeline execution, transition logging, and database writes.
