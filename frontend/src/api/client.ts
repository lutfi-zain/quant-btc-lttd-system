/* eslint-disable @typescript-eslint/no-explicit-any */
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

export interface ChartRecord {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
  final_score: number;
}

export interface RegimeRecord {
  date: string;
  regime: Regime;
  p_bull: number;
  p_bear: number;
  p_sideways: number;
}

export interface DiagnosticsRecord {
  date: string;
  indicator_scores?: Record<string, number>;
  pca_components?: Record<string, number>;
  vif: Record<string, number>;
  pca_variance_explained: number;
}

export interface OnChainRecord {
  date: string;
  sth_mvrv?: number;
  sth_nupl?: number;
  sth_sopr_24h?: number;
}

export async function fetchChartData(start?: string, end?: string): Promise<ChartRecord[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/chart`);
    if (start) url.searchParams.append("start", start);
    if (end) url.searchParams.append("end", end);
    const res = await fetch(url.toString());
    if (!res.ok) throw new APIError(`Failed to fetch chart data: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch chart data");
  }
}

export async function fetchRegimeData(start?: string, end?: string): Promise<RegimeRecord[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/regime`);
    if (start) url.searchParams.append("start", start);
    if (end) url.searchParams.append("end", end);
    const res = await fetch(url.toString());
    if (!res.ok) throw new APIError(`Failed to fetch regime data: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch regime data");
  }
}

export async function fetchDiagnosticsData(start?: string, end?: string): Promise<DiagnosticsRecord[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/diagnostics`);
    if (start) url.searchParams.append("start", start);
    if (end) url.searchParams.append("end", end);
    const res = await fetch(url.toString());
    if (!res.ok) throw new APIError(`Failed to fetch diagnostics data: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch diagnostics data");
  }
}

export async function fetchOnChainData(start?: string, end?: string): Promise<OnChainRecord[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/onchain`);
    if (start) url.searchParams.append("start", start);
    if (end) url.searchParams.append("end", end);
    const res = await fetch(url.toString());
    if (!res.ok) throw new APIError(`Failed to fetch on-chain data: ${res.statusText}`, res.status);
    return await res.json();
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw new APIError(err.message || "Failed to fetch on-chain data");
  }
}

