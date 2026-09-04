import { MOCK_LATENCY, mockResponse } from "@/api/http";
import { MOCK_CONVERSATIONS } from "@/api/mock/mock-data";
import { STORAGE_KEYS, readLocal } from "@/lib/storage";
import type { Conversation } from "@/lib/types";

/** GET /conversations */
export function listConversations(): Promise<Conversation[]> {
  return mockResponse<Conversation[]>(() => {
    const stored = readLocal<Conversation[]>(STORAGE_KEYS.conversations);
    return stored && stored.length > 0 ? stored : MOCK_CONVERSATIONS;
  }, MOCK_LATENCY.fast);
}
