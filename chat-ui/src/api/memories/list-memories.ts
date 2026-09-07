import { http } from "@/api/http";
import type { UserMemoriesResponse } from "@/api/types";

/** Return every active long-term memory owned by the signed-in user. */
export function listMemories(): Promise<UserMemoriesResponse> {
  return http.get<UserMemoriesResponse>("/memories", { cache: "no-store" });
}
