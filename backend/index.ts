import { Hono } from "hono";
import { cors } from "hono/cors";
import { isDbHealthy, getLatestLTTD, getLTTDHistory } from "./db";

export const app = new Hono();

// Enable CORS middleware for local React frontend access
app.use("/api/*", cors());

// Date format validation regex: YYYY-MM-DD
const dateRegex = /^\d{4}-\d{2}-\d{2}$/;

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

export default {
  port: process.env.PORT || 3000,
  fetch: app.fetch,
};
