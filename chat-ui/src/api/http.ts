/**
 * Transport seam for the API layer.
 *
 * Every endpoint under `src/api/**` goes through these helpers, so swapping the
 * mock implementation for a real backend only touches the endpoint files (and,
 * for real HTTP, `request()` below).
 */

export const API_BASE_URL = "/api";

/** Simulated network latency for the mock endpoints (ms). */
export const MOCK_LATENCY = { instant: 0, fast: 120, normal: 260, slow: 520 } as const;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status = 500,
  ) {
    super(message);
    this.name = "ApiError";
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

/** Real-HTTP helper — unused by the mocks today, kept so endpoints can switch over. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw new ApiError(await response.text(), response.status);
  return (await response.json()) as T;
}
