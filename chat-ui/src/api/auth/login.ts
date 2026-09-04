import { http } from "@/api/http";
import type { LoginPayload, LoginResponse, Session } from "@/api/types";
import { setToken } from "@/lib/auth-token";
import { STORAGE_KEYS, writeLocal } from "@/lib/storage";
import { profileFromEmail } from "@/lib/user-profile";

/**
 * POST /auth/login
 *
 * Exchanges credentials for a bearer token, persists the token for the HTTP
 * client, and returns a session. The backend token carries only the user id,
 * so the display profile is derived from the email (same convention the rest
 * of the app uses) until a richer profile endpoint exists.
 *
 * Throws {@link ApiError} on invalid credentials (401), inactive users (403),
 * validation failures (422), server errors (5xx), or network/timeout (0).
 */
export async function login(payload: LoginPayload): Promise<Session> {
  const { access_token } = await http.post<LoginResponse>(
    "/auth/login",
    { email: payload.email.trim().toLowerCase(), password: payload.password },
    { skipAuth: true },
  );

  setToken(access_token);

  const session: Session = {
    signedIn: true,
    user: profileFromEmail(payload.email),
  };
  writeLocal(STORAGE_KEYS.auth, session);
  return session;
}
