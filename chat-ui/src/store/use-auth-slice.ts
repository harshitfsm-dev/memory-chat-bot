import { useCallback, useState } from "react";

import { getSession, signIn as signInRequest, signOut as signOutRequest } from "@/api";
import type { Session } from "@/api/types";
import { GUEST_USER } from "@/lib/defaults";
import { profileFromEmail } from "@/lib/user-profile";

export interface AuthSlice {
  auth: Session;
  loadSession: () => Promise<void>;
  signIn: (email: string, name?: string) => void;
  signOut: () => void;
}

export function useAuthSlice(): AuthSlice {
  const [auth, setAuth] = useState<Session>({ signedIn: false, user: GUEST_USER });

  const loadSession = useCallback(async () => {
    const session = await getSession();
    setAuth(session);
  }, []);

  const signIn = useCallback((email: string, name?: string) => {
    // optimistic: UI updates immediately, endpoint confirms the canonical profile
    setAuth({ signedIn: true, user: profileFromEmail(email, name) });
    void signInRequest({ email, ...(name ? { name } : {}) }).then(setAuth);
  }, []);

  const signOut = useCallback(() => {
    setAuth((prev) => ({ signedIn: false, user: prev.user }));
    void signOutRequest();
  }, []);

  return { auth, loadSession, signIn, signOut };
}
