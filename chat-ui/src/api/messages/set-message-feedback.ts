import { MOCK_LATENCY, mockResponse } from "@/api/http";
import type { MessageFeedbackPayload } from "@/api/types";

/** POST /conversations/:conversationId/messages/:messageId/feedback */
export function setMessageFeedback(payload: MessageFeedbackPayload): Promise<void> {
  return mockResponse<void>(() => {
    void payload;
  }, MOCK_LATENCY.instant);
}
