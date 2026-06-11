import { Database } from "bun:sqlite";
import * as path from "path";
import * as fs from "fs";
import { expect, test, describe, beforeAll, afterAll } from "bun:test";
import { app } from "./index";
import { closeDbConnection } from "./db";

const TEST_DB_PATH = path.resolve(__dirname, "test_lttd.db");

describe("LTTD Backend API", () => {
  beforeAll(() => {
    // Setup test database path environment variable
    process.env.DB_PATH = TEST_DB_PATH;

    // Clean old test DB file if it exists
    if (fs.existsSync(TEST_DB_PATH)) {
      try {
        fs.unlinkSync(TEST_DB_PATH);
      } catch (e) {}
    }

    // Create a new mock database and populate it
    const db = new Database(TEST_DB_PATH);
    db.run("PRAGMA journal_mode=WAL;");
    db.run(`
      CREATE TABLE IF NOT EXISTS daily_lttd (
        data_as_of TEXT PRIMARY KEY,
        date TEXT,
        regime TEXT CHECK(regime IN ('BULL', 'BEAR', 'SIDEWAYS')) NOT NULL,
        final_score REAL CHECK(final_score >= -1.0 AND final_score <= 1.0) NOT NULL,
        target_exposure REAL CHECK(target_exposure >= 0.0 AND target_exposure <= 1.0) NOT NULL,
        posterior_prob REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Insert mock data
    const insert = db.prepare(`
      INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    insert.run("2026-06-01", "2026-06-01", "BULL", 0.8, 0.8, 0.95);
    insert.run("2026-06-02", "2026-06-02", "SIDEWAYS", 0.1, 0.2, 0.60);
    insert.run("2026-06-03", "2026-06-03", "BEAR", -0.5, 0.0, 0.85);
    insert.run("2026-06-04", "2026-06-04", "BEAR", -0.9, 0.0, 0.99);
    insert.run("2026-06-05", "2026-06-05", "BULL", 0.4, 0.5, 0.75);

    db.close();
  });

  afterAll(() => {
    // Make sure we close connections in the db.ts cache to free file locks
    closeDbConnection();

    // Remove the test database files
    const filesToDelete = [
      TEST_DB_PATH,
      `${TEST_DB_PATH}-wal`,
      `${TEST_DB_PATH}-shm`
    ];

    for (const f of filesToDelete) {
      if (fs.existsSync(f)) {
        try {
          fs.unlinkSync(f);
        } catch (e) {}
      }
    }
  });

  describe("GET /api/health", () => {
    test("should return status true when database is healthy", async () => {
      const res = await app.request("/api/health");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body).toEqual({ status: true });
    });

    test("should return status false when database file is missing", async () => {
      process.env.DB_PATH = path.resolve(__dirname, "non_existent.db");
      closeDbConnection(); // Force reconnection to the new path

      const res = await app.request("/api/health");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body).toEqual({ status: false });

      // Restore
      process.env.DB_PATH = TEST_DB_PATH;
      closeDbConnection();
    });
  });

  describe("GET /api/lttd/latest", () => {
    test("should return the latest LTTD record mapping dates, final_score and regime correctly", async () => {
      const res = await app.request("/api/lttd/latest");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body).toHaveProperty("date", "2026-06-05");
      expect(body).toHaveProperty("timestamp", "2026-06-05");
      expect(body).toHaveProperty("final_score", 0.4);
      expect(body).toHaveProperty("regime", "BULL");

      // Verify domain constraints
      expect(body.final_score).toBeGreaterThanOrEqual(-1.0);
      expect(body.final_score).toBeLessThanOrEqual(1.0);
      expect(["BULL", "BEAR", "SIDEWAYS"]).toContain(body.regime);
    });
  });

  describe("GET /api/lttd/history", () => {
    test("should return all records in chronological order", async () => {
      const res = await app.request("/api/lttd/history");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBe(5);

      // Verify chronological sorting (date ASC)
      expect(body[0].date).toBe("2026-06-01");
      expect(body[1].date).toBe("2026-06-02");
      expect(body[2].date).toBe("2026-06-03");
      expect(body[3].date).toBe("2026-06-04");
      expect(body[4].date).toBe("2026-06-05");

      // Verify each record contains domain fields
      for (const record of body) {
        expect(record).toHaveProperty("date");
        expect(record).toHaveProperty("timestamp");
        expect(record).toHaveProperty("final_score");
        expect(record).toHaveProperty("regime");
        expect(record.final_score).toBeGreaterThanOrEqual(-1.0);
        expect(record.final_score).toBeLessThanOrEqual(1.0);
        expect(["BULL", "BEAR", "SIDEWAYS"]).toContain(record.regime);
      }
    });

    test("should filter records with start date bound", async () => {
      const res = await app.request("/api/lttd/history?start=2026-06-03");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body.length).toBe(3);
      expect(body[0].date).toBe("2026-06-03");
      expect(body[1].date).toBe("2026-06-04");
      expect(body[2].date).toBe("2026-06-05");
    });

    test("should filter records with end date bound", async () => {
      const res = await app.request("/api/lttd/history?end=2026-06-03");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body.length).toBe(3);
      expect(body[0].date).toBe("2026-06-01");
      expect(body[1].date).toBe("2026-06-02");
      expect(body[2].date).toBe("2026-06-03");
    });

    test("should filter records with both start and end date bounds", async () => {
      const res = await app.request("/api/lttd/history?start=2026-06-02&end=2026-06-04");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(body.length).toBe(3);
      expect(body[0].date).toBe("2026-06-02");
      expect(body[1].date).toBe("2026-06-03");
      expect(body[2].date).toBe("2026-06-04");
    });

    test("should return 400 bad request for invalid start parameter format", async () => {
      const res = await app.request("/api/lttd/history?start=2026/06/01");
      expect(res.status).toBe(400);
      
      const body = await res.json();
      expect(body.error).toContain("Invalid start date format");
    });

    test("should return 400 bad request for invalid end parameter format", async () => {
      const res = await app.request("/api/lttd/history?end=2026-6-01");
      expect(res.status).toBe(400);
      
      const body = await res.json();
      expect(body.error).toContain("Invalid end date format");
    });
  });

  describe("GET /api/chart", () => {
    test("should return price and score history", async () => {
      const res = await app.request("/api/chart");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBe(5);
      expect(body[0]).toHaveProperty("date");
      expect(body[0]).toHaveProperty("final_score");
    });
  });

  describe("GET /api/regime", () => {
    test("should return regime probabilities summing to 1.0", async () => {
      const res = await app.request("/api/regime");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBe(5);
      
      for (const record of body) {
        expect(record).toHaveProperty("date");
        expect(record).toHaveProperty("regime");
        expect(record).toHaveProperty("p_bull");
        expect(record).toHaveProperty("p_bear");
        expect(record).toHaveProperty("p_sideways");
        
        const sum = record.p_bull + record.p_bear + record.p_sideways;
        expect(Math.abs(sum - 1.0)).toBeLessThan(1e-6);
      }
    });
  });

  describe("GET /api/diagnostics", () => {
    test("should return indicator scores, vif, and pca variance", async () => {
      const res = await app.request("/api/diagnostics");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBe(5);
      expect(body[0]).toHaveProperty("date");
      expect(body[0]).toHaveProperty("vif");
      expect(body[0]).toHaveProperty("pca_variance_explained");
      expect(body[0].pca_variance_explained).toBeGreaterThan(85.0);
    });
  });

  describe("GET /api/onchain", () => {
    test("should return onchain series metrics", async () => {
      const res = await app.request("/api/onchain?start=2026-06-01&end=2026-06-05");
      expect(res.status).toBe(200);
      
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      if (body.length > 0) {
        expect(body[0]).toHaveProperty("date");
        expect(body[0]).toHaveProperty("sth_mvrv");
        expect(body[0]).toHaveProperty("sth_nupl");
      }
    });
  });
});

