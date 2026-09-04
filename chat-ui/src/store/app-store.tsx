import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { Session } from "@/api/types";
import type { Settings } from "@/lib/types";
import { useAuthSlice } from "./use-auth-slice";
import { useConversationsSlice, type ConversationsSlice } from "./use-conversations-slice";
import { useSettingsSlice } from "./use-settings-slice";

export interface AppStore extends ConversationsSlice {
  hydrated: boolean;
  auth: Session;
  logIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => void;
  saveSettings: (next: Settings) => void;
  resolvedTheme: "light" | "dark";
}

const AppContext = createContext<AppStore | null>(null);

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);

  const authSlice = useAuthSlice();
  const settingsSlice = useSettingsSlice(hydrated);
  const conversationsSlice = useConversationsSlice(hydrated, settingsSlice.settings);

  const { loadSession } = authSlice;
  const { loadSettings } = settingsSlice;
  const { loadConversations, clearConversations } = conversationsSlice;
  const signedIn = authSlice.auth.signedIn;

  /* Hydrate local state (session + settings) once on mount. Threads are NOT
     loaded here — they require auth and must not be fetched on the login page. */
  useEffect(() => {
    let active = true;
    void Promise.all([loadSession(), loadSettings()]).finally(() => {
      if (active) setHydrated(true);
    });
    return () => {
      active = false;
    };
  }, [loadSession, loadSettings]);

  /* Load the user's threads only once signed in (i.e. on the chat dashboard);
     clear them on sign-out so a different user never sees stale threads. */
  useEffect(() => {
    if (!hydrated) return;
    if (signedIn) void loadConversations();
    else clearConversations();
  }, [hydrated, signedIn, loadConversations, clearConversations]);

  const { auth, logIn, signOut } = authSlice;
  const { settings, updateSettings, saveSettings, resolvedTheme } = settingsSlice;

  const value = useMemo<AppStore>(
    () => ({
      hydrated,
      auth,
      logIn,
      signOut,
      settings,
      updateSettings,
      saveSettings,
      resolvedTheme,
      ...conversationsSlice,
    }),
    [
      hydrated,
      auth,
      logIn,
      signOut,
      settings,
      updateSettings,
      saveSettings,
      resolvedTheme,
      conversationsSlice,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppStore {
  const store = useContext(AppContext);
  if (!store) throw new Error("useApp must be used inside AppStoreProvider");
  return store;
}
