import { http } from "@/api/http";
import type { ThreadResponse } from "@/api/types";
import type { Conversation } from "@/lib/types";

/**
 * GET /chat/threads
 *
 * Returns the authenticated user's chat threads, most recently updated first.
 * The bearer token is attached by the HTTP client.
 */
export function listThreads(): Promise<ThreadResponse[]> {
  return http.get<ThreadResponse[]>("/chat/threads");
}

/**
 * Maps a backend thread record onto the frontend {@link Conversation} shape.
 *
 * The threads list carries no messages, so `messages` starts empty and is
 * filled lazily when a thread is opened. The backend has no per-thread model
 * or archive flag, so those fall back to sensible defaults.
 */
export function threadToConversation(thread: ThreadResponse): Conversation {
  return {
    id: thread.id,
    title: thread.title ?? "New chat",
    createdAt: thread.created_at,
    updatedAt: thread.updated_at,
    model: "auto",
    archived: false,
    messages: [],
  };
}
