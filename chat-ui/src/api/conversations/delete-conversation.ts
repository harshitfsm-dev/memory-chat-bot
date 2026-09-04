import { MOCK_LATENCY, mockResponse } from "@/api/http";

/** DELETE /conversations/:id */
export function deleteConversation(id: string): Promise<void> {
  return mockResponse<void>(() => {
    void id;
    /* mock: removal is persisted by persist-conversations */
  }, MOCK_LATENCY.instant);
}
