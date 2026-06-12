import { Database } from "bun:sqlite";
import * as path from "path";
import * as fs from "fs";

export interface LTTDRecord {
  date: string;
  timestamp: string;
  final_score: number;
  regime: "BULL" | "BEAR" | "SIDEWAYS";
  target_exposure?: number;
  posterior_prob?: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
  indicator_scores?: Record<string, number>;
  pca_components?: Record<string, number>;
}

export function getDbPath(): string {
  const envPath = process.env.DB_PATH;
  if (envPath) {
    return path.isAbsolute(envPath) ? envPath : path.resolve(process.cwd(), envPath);
  }
  return path.resolve(import.meta.dir, "../database/lttd.db");
}

export function getDbConnection(): Database {
  const dbPath = getDbPath();
  
  if (dbInstance && currentDbPath !== dbPath) {
    dbInstance.close();
    dbInstance = null;
  }

  if (!dbInstance) {
    if (!fs.existsSync(dbPath)) {
      throw new Error(`Database file not found at: ${dbPath}`);
    }
    dbInstance = new Database(dbPath, { readonly: true });
    currentDbPath = dbPath;
    
    // Check WAL mode
    try {
      const res = dbInstance.query("PRAGMA journal_mode;").get() as { journal_mode: string } | null;
      if (res && res.journal_mode !== "wal") {
        console.warn(`Warning: Database is not in WAL mode. Current mode: ${res.journal_mode}`);
      }
    } catch (err) {
      console.error("Failed to check journal mode:", err);
    }
  }
  
  return dbInstance;
}

let dbInstance: Database | null = null;
let currentDbPath: string | null = null;

export function closeDbConnection() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
    currentDbPath = null;
  }
}

export function isDbHealthy(): boolean {
  try {
    const db = getDbConnection();
    db.query("SELECT 1;").get();
    return true;
  } catch (err) {
    console.error("Database health check failed:", err);
    return false;
  }
}

export function getLatestLTTD(): LTTDRecord | null {
  const db = getDbConnection();
  
  // 1. Get latest record from daily_lttd
  const dailyQuery = db.query(`
    SELECT data_as_of, date, regime, final_score, target_exposure, posterior_prob 
    FROM daily_lttd 
    ORDER BY date DESC, data_as_of DESC 
    LIMIT 1
  `);
  const dailyRow = dailyQuery.get() as {
    data_as_of: string;
    date: string;
    regime: string;
    final_score: number;
    target_exposure: number;
    posterior_prob: number | null;
  } | null;
  
  if (!dailyRow) return null;
  const targetDate = dailyRow.date;

  // 2. Fetch ohlcv
  let ohlcvRow: {
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  } | null = null;
  try {
    const ohlcvQuery = db.query(`
      SELECT open, high, low, close, volume 
      FROM ohlcv 
      WHERE SUBSTR(timestamp, 1, 10) = ?
      LIMIT 1
    `);
    ohlcvRow = ohlcvQuery.get(targetDate) as any;
  } catch (e) {
    // Ignore missing table in tests
  }

  // 3. Fetch indicator scores
  const indicatorScores: Record<string, number> = {};
  try {
    const indQuery = db.query(`
      SELECT indicator_name, score 
      FROM indicator_scores 
      WHERE date = ?
    `);
    const indRows = indQuery.all(targetDate) as Array<{ indicator_name: string; score: number }>;
    for (const r of indRows) {
      indicatorScores[r.indicator_name] = r.score;
    }
  } catch (e) {
    // Ignore missing table in tests
  }

  // 4. Fetch pca components
  const pcaComponents: Record<string, number> = {};
  try {
    const pcaQuery = db.query(`
      SELECT component_name, value 
      FROM pca_components 
      WHERE date = ?
    `);
    const pcaRows = pcaQuery.all(targetDate) as Array<{ component_name: string; value: number }>;
    for (const r of pcaRows) {
      pcaComponents[r.component_name] = r.value;
    }
  } catch (e) {
    // Ignore missing table in tests
  }

  return {
    date: dailyRow.date,
    timestamp: dailyRow.data_as_of,
    final_score: dailyRow.final_score,
    regime: dailyRow.regime as "BULL" | "BEAR" | "SIDEWAYS",
    target_exposure: dailyRow.target_exposure,
    posterior_prob: dailyRow.posterior_prob !== null ? dailyRow.posterior_prob : undefined,
    open: ohlcvRow?.open,
    high: ohlcvRow?.high,
    low: ohlcvRow?.low,
    close: ohlcvRow?.close,
    volume: ohlcvRow?.volume,
    indicator_scores: indicatorScores,
    pca_components: pcaComponents
  };
}

export function getLTTDHistory(start?: string, end?: string): LTTDRecord[] {
  const db = getDbConnection();
  
  // 1. Fetch daily LTTD records with date filters
  let dailyQueryStr = `
    SELECT data_as_of, date, regime, final_score, target_exposure, posterior_prob 
    FROM daily_lttd 
    WHERE 1=1
  `;
  const params: Record<string, string> = {};

  if (start) {
    dailyQueryStr += " AND date >= :start";
    params[":start"] = start;
  }
  if (end) {
    dailyQueryStr += " AND date <= :end";
    params[":end"] = end;
  }
  dailyQueryStr += " ORDER BY date ASC, data_as_of ASC";

  const dailyQuery = db.query(dailyQueryStr);
  const dailyRows = dailyQuery.all(params) as Array<{
    data_as_of: string;
    date: string;
    regime: string;
    final_score: number;
    target_exposure: number;
    posterior_prob: number | null;
  }>;

  if (dailyRows.length === 0) return [];

  // Get active dates to filter related tables efficiently
  const dates = dailyRows.map(r => r.date);
  const startBound = dates[0];
  const endBound = dates[dates.length - 1];

  // 2. Fetch all OHLCV records in the date bounds
  const ohlcvMap = new Map<string, {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>();
  try {
    const ohlcvQuery = db.query(`
      SELECT timestamp, open, high, low, close, volume 
      FROM ohlcv 
      WHERE SUBSTR(timestamp, 1, 10) >= ? AND SUBSTR(timestamp, 1, 10) <= ?
    `);
    const ohlcvRows = ohlcvQuery.all(startBound, endBound) as Array<{
      timestamp: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>;
    for (const r of ohlcvRows) {
      const d = r.timestamp.substring(0, 10);
      ohlcvMap.set(d, r);
    }
  } catch (e) {
    // Ignore missing table in tests
  }

  // 3. Fetch all indicator scores in the date bounds
  const indMap = new Map<string, Record<string, number>>();
  try {
    const indQuery = db.query(`
      SELECT date, indicator_name, score 
      FROM indicator_scores 
      WHERE date >= ? AND date <= ?
    `);
    const indRows = indQuery.all(startBound, endBound) as Array<{
      date: string;
      indicator_name: string;
      score: number;
    }>;
    for (const r of indRows) {
      if (!indMap.has(r.date)) {
        indMap.set(r.date, {});
      }
      indMap.get(r.date)![r.indicator_name] = r.score;
    }
  } catch (e) {
    // Ignore missing table in tests
  }

  // 4. Fetch all PCA components in the date bounds
  const pcaMap = new Map<string, Record<string, number>>();
  try {
    const pcaQuery = db.query(`
      SELECT date, component_name, value 
      FROM pca_components 
      WHERE date >= ? AND date <= ?
    `);
    const pcaRows = pcaQuery.all(startBound, endBound) as Array<{
      date: string;
      component_name: string;
      value: number;
    }>;
    for (const r of pcaRows) {
      if (!pcaMap.has(r.date)) {
        pcaMap.set(r.date, {});
      }
      pcaMap.get(r.date)![r.component_name] = r.value;
    }
  } catch (e) {
    // Ignore missing table in tests
  }

  // 5. Assemble composite records
  return dailyRows.map(row => {
    const d = row.date;
    const ohlcv = ohlcvMap.get(d);
    
    return {
      date: row.date,
      timestamp: row.data_as_of,
      final_score: row.final_score,
      regime: row.regime as "BULL" | "BEAR" | "SIDEWAYS",
      target_exposure: row.target_exposure,
      posterior_prob: row.posterior_prob !== null ? row.posterior_prob : undefined,
      open: ohlcv?.open,
      high: ohlcv?.high,
      low: ohlcv?.low,
      close: ohlcv?.close,
      volume: ohlcv?.volume,
      indicator_scores: indMap.get(d) || {},
      pca_components: pcaMap.get(d) || {}
    };
  });
}
