// Deliberately separate from lib/api.ts: the public booking flow has no
// concept of a logged-in user at all (no token to attach, no refresh to
// retry on 401), so reusing apiRequest's auth/refresh machinery here would
// be dead weight at best and a way to accidentally leak a staff session's
// bearer token into a public request at worst.
const PUBLIC_API_BASE = import.meta.env.VITE_PUBLIC_API_BASE_URL ?? "/public";

export class PublicApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

export async function publicApiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${PUBLIC_API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: { "Content-Type": "application/json" },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw new PublicApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
