import axios from "axios";
import type { Analytics, HistoryPage, ScoreRequestPayload, ScoreResponse } from "./types";

const DEFAULT_BASE = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

export function getApiKey(): string {
  return localStorage.getItem("creditpulse_api_key") || "cp_demo_fnb_business_key_do_not_use_in_prod";
}

export function setApiKey(key: string): void {
  localStorage.setItem("creditpulse_api_key", key);
}

export const api = axios.create({
  baseURL: DEFAULT_BASE,
});

api.interceptors.request.use((config) => {
  config.headers["X-API-Key"] = getApiKey();
  return config;
});

export async function requestScore(payload: ScoreRequestPayload): Promise<ScoreResponse> {
  const { data } = await api.post<ScoreResponse>("/v1/score", payload);
  return data;
}

export async function fetchScore(id: string): Promise<ScoreResponse> {
  const { data } = await api.get<ScoreResponse>(`/v1/score/${id}`);
  return data;
}

export async function fetchHistory(params: Record<string, any> = {}): Promise<HistoryPage> {
  const { data } = await api.get<HistoryPage>("/v1/history", { params });
  return data;
}

export async function fetchAnalytics(): Promise<Analytics> {
  const { data } = await api.get<Analytics>("/v1/analytics/overview");
  return data;
}

export async function health(): Promise<{ status: string }> {
  const { data } = await api.get("/health");
  return data;
}
