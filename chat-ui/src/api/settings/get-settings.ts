import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { DEFAULT_SETTINGS } from "@/lib/defaults";
import { STORAGE_KEYS, readLocal } from "@/lib/storage";
import type { Settings } from "@/lib/types";

/** GET /settings */
export function getSettings(): Promise<Settings> {
  return mockResponse<Settings>(() => {
    const stored = readLocal<Settings>(STORAGE_KEYS.settings);
    return stored ? { ...DEFAULT_SETTINGS, ...stored } : DEFAULT_SETTINGS;
  }, MOCK_LATENCY.fast);
}
