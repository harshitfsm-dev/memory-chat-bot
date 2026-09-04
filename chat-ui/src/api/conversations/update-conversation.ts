import { MOCK_LATENCY, mockResponse } from "@/api/http";
import type { ConversationPatch } from "@/api/types";

/** PATCH /conversations/:id */
export function updateConversation(id: string, patch: ConversationPatch): Promise<void> {
  return mockResponse<void>(() => {
    void id;
    void patch;
    /* mock: the store holds the source of truth and persists via persist-conversations */
  }, MOCK_LATENCY.instant);
}
