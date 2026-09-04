/**
 * Transport seam for the API layer.
 *
 * Every endpoint under `src/api/**` goes through these helpers. This is the one
 * place that knows about the backend: base URL, auth headers, timeouts, JSON
 * encoding, and error normalization all live here so feature endpoints stay
 * thin and UI code never touches `fetch`.
 *
 * Endpoints still on mock data use `mockResponse`; endpoints wired to the real
 * backend use `request` / the `http` verb helpers.
 */
import { clearToken, getToken } from "@/lib/auth-token";

/**
 * Base URL for backend calls. Defaults to the same-origin `/api` prefix (the
 * Vite dev server proxies it to the backend). Override with `VITE_API_BASE_URL`
 * for a deployed API on another origin.
 */
export const API_BASE_URL: string =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined)?.replace(/\/$/, "") ?? "/api";

/** Default per-request timeout (ms). */
const DEFAULT_TIMEOUT_MS = 15_000;

/** Simulated network latency for the mock endpoints (ms). */
export const MOCK_LATENCY = { instant: 0, fast: 120, normal: 260, slow: 520 } as const;

/**
 * Normalized transport error. Carries the HTTP status (0 = network/timeout)
 * so callers can branch on it (e.g. 401 → invalid credentials) without parsing
 * strings.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status = 500,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Wraps a mock resolver so endpoints keep a Promise-based, async-only contract. */
export async function mockResponse<T>(
  resolve: () => T | Promise<T>,
  latency: number = MOCK_LATENCY.normal,
): Promise<T> {
  await sleep(latency);
  return resolve();
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON-serializable request body. */
  body?: unknown;
  /** Per-request timeout override (ms). */
  timeoutMs?: number;
  /** Skip attaching the Authorization header (e.g. for login). */
  skipAuth?: boolean;
}

/** Pulls the human-readable message out of a FastAPI-style error body. */
function messageFromBody(body: unknown, fallback: string): string {
  if (typeof body === "string" && body.trim()) return body;
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    // Pydantic 422 returns detail as an array of validation errors.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === "string") return first.msg;
    }
  }
  return fallback;
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => undefined);
  }
  const text = await response.text().catch(() => "");
  return text || undefined;
}

/**
 * Core HTTP helper. Handles base URL, JSON encoding, auth header injection,
 * timeouts, and error normalization. Returns `undefined` for 204/empty bodies.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, timeoutMs = DEFAULT_TIMEOUT_MS, skipAuth = false, headers, ...init } = options;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const finalHeaders = new Headers(headers);
  if (body !== undefined && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (!skipAuth) {
    const token = getToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: finalHeaders,
      signal: init.signal ?? controller.signal,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out. Please try again.", 0);
    }
    throw new ApiError("Unable to reach the server. Check your connection.", 0);
  }
  clearTimeout(timeout);

  const payload = await parseBody(response);

  if (!response.ok) {
    // A 401 means the stored token is no longer valid — drop it so the app
    // falls back to the signed-out state on next hydration.
    if (response.status === 401 && !skipAuth) clearToken();
    throw new ApiError(
      messageFromBody(payload, `Request failed with status ${response.status}`),
      response.status,
      payload,
    );
  }

  return payload as T;
}

/** Thin verb helpers so endpoints read declaratively. */
export const http = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
} as const;
