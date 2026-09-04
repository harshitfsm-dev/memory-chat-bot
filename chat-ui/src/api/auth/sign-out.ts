import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { STORAGE_KEYS, readLocal, writeLocal } from "@/lib/storage";
import type { Session } from "@/api/types";

/** POST /auth/sign-out */
export function signOut(): Promise<void> {
  return mockResponse<void>(() => {
    const stored = readLocal<Session>(STORAGE_KEYS.auth);
    if (stored) writeLocal(STORAGE_KEYS.auth, { ...stored, signedIn: false });
  }, MOCK_LATENCY.fast);
}
