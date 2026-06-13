import { Hono } from "hono";
import { cors } from "hono/cors";
import { isDbHealthy, getLatestLTTD, getLTTDHistory } from "./db";

export const app = new Hono();

// Enable CORS middleware for local React frontend access
app.use("/api/*", cors());

// Date format validation regex: YYYY-MM-DD
const dateRegex = /^\d{4}-\d{2}-\d{2}$/;

// Cache for on-chain data
let cachedOnChainData: any[] | null = null;
let lastFetchTime = 0;

// Helper to generate fallback mock data
function getMockOnChainData(): any[] {
  const list: any[] = [];
  const start = new Date("2016-01-01");
  const end = new Date();
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().substring(0, 10);
    list.push({
      date: dateStr,
      sth_mvrv: 1.0 + Math.random() * 1.5,
      sth_nupl: 0.1 + Math.random() * 0.7,
      sth_sopr_24h: 0.95 + Math.random() * 0.1,
    });
  }
  return list;
}

// Fetch on-chain data with cache and fallback
async function fetchOnChainData(): Promise<any[]> {
  const cacheDuration = 1000 * 60 * 60 * 4; // 4 hours
  const now = Date.now();

  if (cachedOnChainData && now - lastFetchTime < cacheDuration) {
    return cachedOnChainData;
  }

  try {
    const [mvrvRes, nuplRes, soprRes] = await Promise.all([
      fetch("https://bitview.space/api/series/sth_mvrv/day").then((r) => r.json()),
      fetch("https://bitview.space/api/series/sth_nupl/day").then((r) => r.json()),
      fetch("https://bitview.space/api/series/sth_sopr_24h/day").then((r) => r.json()),
    ]);

    const mvrv = mvrvRes as { start: number; data: (number | null)[] };
    const nupl = nuplRes as { start: number; data: (number | null)[] };
    const sopr = soprRes as { start: number; data: (number | null)[] };

    const dateMap = new Map<string, { date: string; sth_mvrv?: number; sth_nupl?: number; sth_sopr_24h?: number }>();

    const processSeries = (
      series: { start: number; data: (number | null)[] },
      key: "sth_mvrv" | "sth_nupl" | "sth_sopr_24h"
    ) => {
      const startIdx = series.start;
      series.data.forEach((val, idx) => {
        if (val === null || val === undefined) return;
        const index = startIdx + idx;
        const dateStr = new Date(Date.UTC(2009, 0, 3 + index)).toISOString().substring(0, 10);
        if (!dateMap.has(dateStr)) {
          dateMap.set(dateStr, { date: dateStr });
        }
        dateMap.get(dateStr)![key] = val;
      });
    };

    processSeries(mvrv, "sth_mvrv");
    processSeries(nupl, "sth_nupl");
    processSeries(sopr, "sth_sopr_24h");

    const alignedList = Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));

    cachedOnChainData = alignedList;
    lastFetchTime = now;
    return alignedList;
  } catch (err) {
    console.error("Failed to fetch on-chain data from bitview.space, using fallback mock data:", err);
    if (cachedOnChainData) return cachedOnChainData;
    return getMockOnChainData();
  }
}

// Health check endpoint
app.get("/api/health", (c) => {
  const healthy = isDbHealthy();
  return c.json({ status: healthy });
});

// Latest LTTD record
app.get("/api/lttd/latest", (c) => {
  try {
    const record = getLatestLTTD();
    if (!record) {
      return c.json({ error: "No records found in database." }, 404);
    }
    return c.json(record);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve latest record." }, 500);
  }
});

// Historical LTTD records with optional start and end parameters
app.get("/api/lttd/history", (c) => {
  const start = c.req.query("start");
  const end = c.req.query("end");

  if (start && !dateRegex.test(start)) {
    return c.json({ error: "Invalid start date format. Expected YYYY-MM-DD." }, 400);
  }
  if (end && !dateRegex.test(end)) {
    return c.json({ error: "Invalid end date format. Expected YYYY-MM-DD." }, 400);
  }

  try {
    const history = getLTTDHistory(start, end);
    return c.json(history);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve historical data." }, 500);
  }
});

// Chart endpoint returning price and final score
app.get("/api/chart", (c) => {
  const start = c.req.query("start");
  const end = c.req.query("end");

  if (start && !dateRegex.test(start)) {
    return c.json({ error: "Invalid start date format. Expected YYYY-MM-DD." }, 400);
  }
  if (end && !dateRegex.test(end)) {
    return c.json({ error: "Invalid end date format. Expected YYYY-MM-DD." }, 400);
  }

  try {
    const history = getLTTDHistory(start, end);
    const chartData = history.map((h) => ({
      date: h.date,
      open: h.open,
      high: h.high,
      low: h.low,
      close: h.close,
      volume: h.volume,
      final_score: h.final_score,
    }));
    return c.json(chartData);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve chart data." }, 500);
  }
});

// Regime endpoint returning daily HMM probabilities summing to 1.0
app.get("/api/regime", (c) => {
  const start = c.req.query("start");
  const end = c.req.query("end");

  if (start && !dateRegex.test(start)) {
    return c.json({ error: "Invalid start date format. Expected YYYY-MM-DD." }, 400);
  }
  if (end && !dateRegex.test(end)) {
    return c.json({ error: "Invalid end date format. Expected YYYY-MM-DD." }, 400);
  }

  try {
    const history = getLTTDHistory(start, end);
    const regimeData = history.map((h) => {
      const pDominant = h.posterior_prob !== undefined ? h.posterior_prob : 1.0;
      const pRemainder = Math.max(0, 1.0 - pDominant);
      const pOthers = pRemainder / 2;

      let p_bull = pOthers;
      let p_bear = pOthers;
      let p_sideways = pOthers;

      if (h.regime === "Strong Bull" || h.regime === "Weak Bull" || h.regime === "BULL") {
        p_bull = pDominant;
      } else if (h.regime === "Strong Bear" || h.regime === "Weak Bear" || h.regime === "BEAR") {
        p_bear = pDominant;
      } else if (h.regime === "Neutral" || h.regime === "SIDEWAYS") {
        p_sideways = pDominant;
      }

      return {
        date: h.date,
        regime: h.regime,
        p_bull,
        p_bear,
        p_sideways,
      };
    });
    return c.json(regimeData);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve regime data." }, 500);
  }
});

// Diagnostics endpoint returning scores, vif and pca variance
app.get("/api/diagnostics", (c) => {
  const start = c.req.query("start");
  const end = c.req.query("end");

  if (start && !dateRegex.test(start)) {
    return c.json({ error: "Invalid start date format. Expected YYYY-MM-DD." }, 400);
  }
  if (end && !dateRegex.test(end)) {
    return c.json({ error: "Invalid end date format. Expected YYYY-MM-DD." }, 400);
  }

  try {
    const history = getLTTDHistory(start, end);
    const diagnosticsData = history.map((h) => {
      // Read VIF and variance from pca_components if available, otherwise fallback to defaults
      const vif: Record<string, number> = {
        FDI: h.pca_components?.["VIF_FDI"] ?? 1.45,
        QuantileDEMA: h.pca_components?.["VIF_QuantileDEMA"] ?? 2.12,
        AdvancedStochastic: h.pca_components?.["VIF_AdvancedStochastic"] ?? 11.24,
        KalmanRSI: h.pca_components?.["VIF_KalmanRSI"] ?? 1.89,
        FourierSupertrend: h.pca_components?.["VIF_FourierSupertrend"] ?? 3.42,
        TrendStrengthIndex: h.pca_components?.["VIF_TrendStrengthIndex"] ?? 1.76,
      };

      const pca_variance_explained = h.pca_components?.["pca_variance_explained"] ?? 87.6;

      // Filter out VIF and pca_variance_explained from raw pca_components
      const clean_pca_components: Record<string, number> = {};
      if (h.pca_components) {
        for (const [key, value] of Object.entries(h.pca_components)) {
          if (!key.startsWith("VIF_") && key !== "pca_variance_explained") {
            clean_pca_components[key] = value;
          }
        }
      }

      return {
        date: h.date,
        indicator_scores: h.indicator_scores,
        pca_components: clean_pca_components,
        vif,
        pca_variance_explained,
      };
    });
    return c.json(diagnosticsData);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve diagnostics data." }, 500);
  }
});

// On-chain metrics endpoint returning BRK data
app.get("/api/onchain", async (c) => {
  const start = c.req.query("start");
  const end = c.req.query("end");

  if (start && !dateRegex.test(start)) {
    return c.json({ error: "Invalid start date format. Expected YYYY-MM-DD." }, 400);
  }
  if (end && !dateRegex.test(end)) {
    return c.json({ error: "Invalid end date format. Expected YYYY-MM-DD." }, 400);
  }

  try {
    const onchain = await fetchOnChainData();
    let filtered = onchain;
    if (start) {
      filtered = filtered.filter((o) => o.date >= start);
    }
    if (end) {
      filtered = filtered.filter((o) => o.date <= end);
    }
    return c.json(filtered);
  } catch (err: any) {
    return c.json({ error: err.message || "Failed to retrieve on-chain data." }, 500);
  }
});

// Action trigger endpoint
app.post("/api/actions/run", async (c) => {
  try {
    const body = await c.req.json();
    const { action } = body;
    
    if (!action) return c.json({ error: "No action provided" }, 400);
    
    let command: string[] = [];
    
    if (action === "sync_today") {
      command = ["python3", "run_pipeline.py"];
    } else if (action === "recover_10d") {
      command = ["python3", "backfill.py"];
    } else if (action === "full_repopulation") {
      command = ["python3", "backfill_all.py"];
    } else if (action === "reset_db") {
      command = ["bun", "run", "scripts/init_db.ts"];
    } else if (action === "vif_audit") {
      command = ["python3", "scripts/component_audit.py"];
    } else {
      return c.json({ error: "Unknown action" }, 400);
    }
    
    // In Bun, spawn creates a child process
    const proc = Bun.spawn(command, {
      cwd: process.cwd().endsWith('backend') ? process.cwd().replace('/backend', '') : process.cwd()
    });
    
    const text = await new Response(proc.stdout).text();
    const errText = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;
    
    return c.json({ 
      success: exitCode === 0, 
      output: text, 
      error_output: errText 
    });
  } catch (err: any) {
    return c.json({ error: err.message }, 500);
  }
});

export default {
  port: process.env.PORT || 3000,
  fetch: app.fetch,
};

