import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { clearToken } from "@/lib/auth-token";
import { STORAGE_KEYS, readLocal, writeLocal } from "@/lib/storage";
import type { Session } from "@/api/types";

/**
 * Sign out.
 *
 * The backend uses stateless JWTs, so there is nothing to revoke server-side —
 * clearing the local token and flipping the persisted session is enough.
 */
export function signOut(): Promise<void> {
  return mockResponse<void>(() => {
    clearToken();
    const stored = readLocal<Session>(STORAGE_KEYS.auth);
    if (stored) writeLocal(STORAGE_KEYS.auth, { ...stored, signedIn: false });
  }, MOCK_LATENCY.fast);
}
