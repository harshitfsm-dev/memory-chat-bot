import { MOCK_LATENCY, mockResponse } from "@/api/http";
import type { Session, SignInPayload } from "@/api/types";
import { STORAGE_KEYS, writeLocal } from "@/lib/storage";
import { profileFromEmail } from "@/lib/user-profile";

/** POST /auth/sign-in */
export function signIn(payload: SignInPayload): Promise<Session> {
  return mockResponse<Session>(() => {
    const session: Session = {
      signedIn: true,
      user: profileFromEmail(payload.email, payload.name),
    };
    writeLocal(STORAGE_KEYS.auth, session);
    return session;
  }, MOCK_LATENCY.normal);
}
