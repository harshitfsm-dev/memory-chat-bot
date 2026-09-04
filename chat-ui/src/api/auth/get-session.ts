import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { MOCK_USER } from "@/api/mock/mock-data";
import type { Session } from "@/api/types";
import { STORAGE_KEYS, readLocal } from "@/lib/storage";

/** GET /auth/session */
export function getSession(): Promise<Session> {
  return mockResponse<Session>(() => {
    const stored = readLocal<Session>(STORAGE_KEYS.auth);
    if (stored) return { signedIn: stored.signedIn, user: stored.user };
    return { signedIn: false, user: MOCK_USER };
  }, MOCK_LATENCY.fast);
}
