import { useCallback, useEffect, useState } from "react";

import { getSettings, saveSettings as saveSettingsRequest } from "@/api";
import { DEFAULT_SETTINGS } from "@/lib/defaults";
import type { Settings } from "@/lib/types";

export interface SettingsSlice {
  settings: Settings;
  resolvedTheme: "light" | "dark";
  loadSettings: () => Promise<void>;
  updateSettings: (patch: Partial<Settings>) => void;
  saveSettings: (next: Settings) => void;
}

/** Owns settings state, theme resolution and DOM theming side effects. */
export function useSettingsSlice(hydrated: boolean): SettingsSlice {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [systemDark, setSystemDark] = useState(false);

  const loadSettings = useCallback(async () => {
    setSettings(await getSettings());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemDark(query.matches);
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const resolvedTheme: "light" | "dark" =
    settings.theme === "system" ? (systemDark ? "dark" : "light") : settings.theme;

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", resolvedTheme === "dark");
    root.classList.toggle("no-anim", !settings.animations);
    root.dataset["density"] = settings.compactMode ? "compact" : "comfortable";
  }, [resolvedTheme, settings.animations, settings.compactMode]);

  useEffect(() => {
    if (!hydrated) return;
    void saveSettingsRequest(settings);
  }, [settings, hydrated]);

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  }, []);

  const saveSettings = useCallback((next: Settings) => setSettings(next), []);

  return { settings, resolvedTheme, loadSettings, updateSettings, saveSettings };
}
