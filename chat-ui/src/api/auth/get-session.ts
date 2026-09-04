import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { getToken } from "@/lib/auth-token";
import type { Session } from "@/api/types";
import { GUEST_USER } from "@/lib/defaults";
import { STORAGE_KEYS, readLocal } from "@/lib/storage";

/**
 * GET /auth/session
 *
 * Resolves the current session from local state. A session counts as signed-in
 * only when a bearer token is present, so a stale persisted profile without a
 * token correctly reads as signed-out. Rehydrated synchronously today; when a
 * profile endpoint exists this is where we would validate the token server-side.
 */
export function getSession(): Promise<Session> {
  return mockResponse<Session>(() => {
    const hasToken = getToken() !== null;
    const stored = readLocal<Session>(STORAGE_KEYS.auth);

    if (hasToken && stored) {
      return { signedIn: true, user: stored.user };
    }
    return { signedIn: false, user: stored?.user ?? GUEST_USER };
  }, MOCK_LATENCY.fast);
}
