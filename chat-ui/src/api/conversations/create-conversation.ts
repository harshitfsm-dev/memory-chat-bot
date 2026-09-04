import { MOCK_LATENCY, mockResponse } from "@/api/http";
import type { CreateConversationPayload } from "@/api/types";
import { createId } from "@/lib/id";
import type { Conversation } from "@/lib/types";

/**
 * POST /conversations
 *
 * Returns the created record so the server owns id/timestamps once this becomes
 * a real endpoint. The mock builds the same shape locally.
 */
export function createConversation(payload: CreateConversationPayload): Promise<Conversation> {
  return mockResponse<Conversation>(() => {
    const stamp = new Date().toISOString();
    return {
      id: payload.id ?? createId(),
      title: payload.title ?? "New chat",
      createdAt: stamp,
      updatedAt: stamp,
      model: payload.model,
      archived: false,
      messages: [],
    };
  }, MOCK_LATENCY.instant);
}
