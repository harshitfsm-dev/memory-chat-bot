import { useCallback, useState } from "react";

import { getSession, login as loginRequest, signOut as signOutRequest } from "@/api";
import { ApiError } from "@/api/http";
import type { Session } from "@/api/types";
import { GUEST_USER } from "@/lib/defaults";

export interface AuthSlice {
  auth: Session;
  loadSession: () => Promise<void>;
  logIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

export function useAuthSlice(): AuthSlice {
  const [auth, setAuth] = useState<Session>({ signedIn: false, user: GUEST_USER });

  const loadSession = useCallback(async () => {
    const session = await getSession();
    setAuth(session);
  }, []);

  /**
   * Authenticate against the backend. Resolves on success (state updated) and
   * rejects with an {@link ApiError} the UI can render. Auth state is only
   * flipped after the token is confirmed — no optimistic sign-in.
   */
  const logIn = useCallback(async (email: string, password: string) => {
    try {
      const session = await loginRequest({ email, password });
      setAuth(session);
    } catch (error) {
      throw error instanceof ApiError
        ? error
        : new ApiError("Something went wrong. Please try again.", 0);
    }
  }, []);

  const signOut = useCallback(() => {
    setAuth((prev) => ({ signedIn: false, user: prev.user }));
    void signOutRequest();
  }, []);

  return { auth, loadSession, logIn, signOut };
}
