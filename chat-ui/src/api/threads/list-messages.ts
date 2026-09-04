import { http } from "@/api/http";
import type { MessageResponse } from "@/api/types";
import type { ChatMessage } from "@/lib/types";

/**
 * GET /chat/messages?thread_id={id}
 *
 * Returns the transcript for a thread the caller owns, oldest message first.
 * Rejects with an {@link ApiError} (404) when the thread does not exist or is
 * not owned by the caller.
 */
export function listMessages(threadId: string): Promise<MessageResponse[]> {
  const query = new URLSearchParams({ thread_id: threadId });
  return http.get<MessageResponse[]>(`/chat/messages?${query.toString()}`);
}

/**
 * Maps a backend message record onto the frontend {@link ChatMessage} shape.
 *
 * The backend stores `role` as a free string; anything other than "user" is
 * treated as an assistant turn. Feedback is not persisted server-side, so it
 * starts null.
 */
export function messageToChatMessage(message: MessageResponse): ChatMessage {
  return {
    id: message.id,
    role: message.role === "user" ? "user" : "assistant",
    content: message.content,
    createdAt: message.created_at,
    feedback: null,
  };
}
