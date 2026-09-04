import { streamMockCompletion } from "@/api/mock/mock-stream";
import type {
  CompletionStream,
  StreamCompletionCallbacks,
  StreamCompletionPayload,
} from "@/api/types";

/**
 * POST /conversations/:id/completions (streaming)
 *
 * Callers get a `CompletionStream`; the transport is an implementation detail of
 * this file. A real backend would open an SSE/fetch stream here and call the
 * same `onDelta` / `onFinish` callbacks.
 */
export function streamCompletion(
  payload: StreamCompletionPayload,
  callbacks: StreamCompletionCallbacks,
): CompletionStream {
  const handle = streamMockCompletion({
    prompt: payload.prompt,
    history: payload.history,
    settings: payload.settings,
    onDelta: callbacks.onDelta,
    onFinish: callbacks.onFinish,
  });

  return { stop: handle.stop, done: handle.done };
}
