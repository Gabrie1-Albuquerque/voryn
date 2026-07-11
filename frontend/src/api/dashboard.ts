import { apiRequest } from "../lib/api";
import type { DashboardSummary } from "./types";

export function getDashboardSummary(start?: string, end?: string): Promise<DashboardSummary> {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const query = params.toString();
  return apiRequest(`/dashboard/summary${query ? `?${query}` : ""}`);
}
