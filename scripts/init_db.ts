import { Database } from "bun:sqlite";
import * as fs from "fs";
import * as path from "path";

const dbPath = path.resolve(import.meta.dir, "../database/lttd.db");
const dbDir = path.dirname(dbPath);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}
const db = new Database(dbPath);
db.exec("PRAGMA journal_mode=WAL;");
db.exec(`
CREATE TABLE IF NOT EXISTS daily_lttd (
    data_as_of TEXT PRIMARY KEY,
    date TEXT,
    regime TEXT CHECK(regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
    final_score REAL CHECK(final_score >= 0.0 AND final_score <= 1.0) NOT NULL,
    target_exposure REAL CHECK(target_exposure >= 0.0 AND target_exposure <= 1.0) NOT NULL,
    posterior_prob REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS indicator_scores (
    date TEXT,
    indicator_name TEXT,
    score REAL CHECK(score >= 0.0 AND score <= 1.0) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, indicator_name)
);
CREATE TABLE IF NOT EXISTS pca_components (
    date TEXT,
    component_name TEXT,
    value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, component_name)
);
CREATE TABLE IF NOT EXISTS regime_transitions (
    transition_date TEXT PRIMARY KEY,
    previous_regime TEXT CHECK(previous_regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')),
    new_regime TEXT CHECK(new_regime IN ('Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear', 'BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
    posterior_probability REAL,
    triggering_metrics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ohlcv (
    timestamp TEXT PRIMARY KEY,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL
);
`);
db.close();
console.log("Database initialized at", dbPath);
