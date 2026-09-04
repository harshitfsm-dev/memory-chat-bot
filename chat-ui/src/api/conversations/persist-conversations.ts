import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { STORAGE_KEYS, removeLocal, writeLocal } from "@/lib/storage";
import type { Conversation } from "@/lib/types";

/**
 * Mock-only durability hook (local cache). With a real backend this becomes a
 * no-op because each mutation endpoint already persists server-side.
 */
export function persistConversations(
  conversations: Conversation[],
  enabled = true,
): Promise<void> {
  return mockResponse<void>(() => {
    if (enabled) writeLocal(STORAGE_KEYS.conversations, conversations);
    else removeLocal(STORAGE_KEYS.conversations);
  }, MOCK_LATENCY.instant);
}
