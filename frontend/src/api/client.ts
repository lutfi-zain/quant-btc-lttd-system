export type Regime = "BULL" | "BEAR" | "SIDEWAYS";

export interface LTTDRecord {
  date: string;
  timestamp: string;
  final_score: number;
  regime: Regime;
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

export interface HealthStatus {
  status: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

/**
 * Custom Error class for API call failures
 */
export class APIError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "APIError";
    this.status = status;
  }
}

/**
 * Fetches the health status of the database/backend.
 */
export async function fetchHealthStatus(): Promise<HealthStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) {
      throw new APIError(`HTTP error! status: ${res.status}`, res.status);
    }
    return await res.json();
  } catch (err: any) {
    throw new APIError(err.message || "Failed to fetch health status");
  }
}

/**
 * Fetches the latest LTTD evaluation record.
 */
export async function fetchLatestLTTD(): Promise<LTTDRecord> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/lttd/latest`);
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new APIError(
        errorBody.error || `HTTP error! status: ${res.status}`,
        res.status
      );
    }
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch latest LTTD record");
  }
}

/**
 * Fetches the historical LTTD evaluation records within an optional date range.
 * Dates should be formatted as YYYY-MM-DD.
 */
export async function fetchLTTDHistory(
  start?: string,
  end?: string
): Promise<LTTDRecord[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/lttd/history`);
    if (start) url.searchParams.append("start", start);
    if (end) url.searchParams.append("end", end);

    const res = await fetch(url.toString());
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new APIError(
        errorBody.error || `HTTP error! status: ${res.status}`,
        res.status
      );
    }
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch LTTD history");
  }
}
