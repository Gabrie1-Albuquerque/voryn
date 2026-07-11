import { tokenStore } from "./tokenStore";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

// Concurrent 401s must share one refresh attempt, not each fire their own
// (that would race multiple refreshes against the same rotating refresh
// token -- see backend/services/auth_service.py's single-use rotation --
// and only the first would actually succeed).
let refreshPromise: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = tokenStore.getRefreshToken();
    if (!refreshToken) return false;
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      tokenStore.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    }
  })();
  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  authenticated?: boolean;
}

async function rawRequest(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.authenticated !== false) {
    const token = tokenStore.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await rawRequest(path, options);

  if (response.status === 401 && options.authenticated !== false) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      response = await rawRequest(path, options);
    } else {
      tokenStore.emitLoggedOut();
      throw new ApiError(401, "session expired");
    }
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
