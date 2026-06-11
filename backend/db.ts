import { Database } from "bun:sqlite";
import * as path from "path";
import * as fs from "fs";

let dbInstance: Database | null = null;
let currentDbPath: string | null = null;

export interface LTTDRecord {
  date: string;
  timestamp: string;
  final_score: number;
  regime: "BULL" | "BEAR" | "SIDEWAYS";
}

export function getDbPath(): string {
  const envPath = process.env.DB_PATH;
  if (envPath) {
    return path.isAbsolute(envPath) ? envPath : path.resolve(process.cwd(), envPath);
  }
  return path.resolve(process.cwd(), "database/lttd.db");
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
  const query = db.query(`
    SELECT data_as_of, date, final_score, regime 
    FROM daily_lttd 
    ORDER BY date DESC, data_as_of DESC 
    LIMIT 1
  `);
  const row = query.get() as { data_as_of: string; date: string; final_score: number; regime: string } | null;
  if (!row) return null;
  return {
    date: row.date,
    timestamp: row.data_as_of,
    final_score: row.final_score,
    regime: row.regime as "BULL" | "BEAR" | "SIDEWAYS"
  };
}

export function getLTTDHistory(start?: string, end?: string): LTTDRecord[] {
  const db = getDbConnection();
  let queryStr = "SELECT data_as_of, date, final_score, regime FROM daily_lttd WHERE 1=1";
  const params: Record<string, string> = {};

  if (start) {
    queryStr += " AND date >= :start";
    params[":start"] = start;
  }
  if (end) {
    queryStr += " AND date <= :end";
    params[":end"] = end;
  }
  queryStr += " ORDER BY date ASC, data_as_of ASC";

  const query = db.query(queryStr);
  const rows = query.all(params) as Array<{ data_as_of: string; date: string; final_score: number; regime: string }>;
  
  return rows.map(row => ({
    date: row.date,
    timestamp: row.data_as_of,
    final_score: row.final_score,
    regime: row.regime as "BULL" | "BEAR" | "SIDEWAYS"
  }));
}
