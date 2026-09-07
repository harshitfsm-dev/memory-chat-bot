import { http } from "@/api/http";

/** Soft-delete one active memory owned by the signed-in user. */
export function forgetMemory(memoryId: string, updatedAt: string): Promise<void> {
  const version = encodeURIComponent(updatedAt);
  return http.delete<void>(`/memories/${encodeURIComponent(memoryId)}?updated_at=${version}`);
}
