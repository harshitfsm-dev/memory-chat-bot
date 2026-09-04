import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { deriveTitle } from "@/api/mock/mock-stream";

/** POST /conversations/:id/title */
export function generateTitle(prompt: string): Promise<string> {
  return mockResponse<string>(() => deriveTitle(prompt), MOCK_LATENCY.instant);
}

/** Synchronous optimistic title, used for instant UI feedback. */
export { deriveTitle as optimisticTitle };
