import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { STORAGE_KEYS, writeLocal } from "@/lib/storage";
import type { Settings } from "@/lib/types";

/** PUT /settings */
export function saveSettings(settings: Settings): Promise<Settings> {
  return mockResponse<Settings>(() => {
    writeLocal(STORAGE_KEYS.settings, settings);
    return settings;
  }, MOCK_LATENCY.instant);
}
