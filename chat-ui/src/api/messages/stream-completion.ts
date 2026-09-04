import { API_BASE_URL, ApiError, notifyUnauthorized } from "@/api/http";
import type {
  CompletionStream,
  StreamCompletionCallbacks,
  StreamCompletionPayload,
} from "@/api/types";
import { getToken } from "@/lib/auth-token";

/**
 * POST /chat/stream (Server-Sent Events)
 *
 * Opens a streaming completion against the backend and adapts its SSE frames
 * (`meta` / `delta` / `done` / `error`) onto the caller's callbacks. `onDelta`
 * receives the cumulative text so far, matching the store's rendering model.
 *
 * The returned handle can `stop()` the stream (aborts the request) and exposes
 * a `done` promise that resolves once the stream ends or is aborted.
 */
export function streamCompletion(
  payload: StreamCompletionPayload,
  callbacks: StreamCompletionCallbacks,
): CompletionStream {
  const controller = new AbortController();
  let aborted = false;
  let text = "";

  const done = (async (): Promise<{ text: string; aborted: boolean }> => {
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: payload.prompt,
          thread_id: payload.threadId,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        // Token expired/invalid mid-session — clear it and route to login.
        if (response.status === 401) notifyUnauthorized();
        throw new ApiError(`Chat stream failed with status ${response.status}`, response.status);
      }

      await consumeSse(response.body, {
        onEvent: (event, data) => {
          if (event === "meta") {
            const id = typeof data["thread_id"] === "string" ? data["thread_id"] : null;
            const title = typeof data["thread_title"] === "string" ? data["thread_title"] : "";
            if (id) callbacks.onMeta?.(id, title);
          } else if (event === "delta") {
            if (typeof data["text"] === "string") {
              text += data["text"];
              callbacks.onDelta(text);
            }
          } else if (event === "done") {
            if (typeof data["text"] === "string" && data["text"]) text = data["text"];
          } else if (event === "error") {
            const detail =
              typeof data["text"] === "string" && data["text"]
                ? data["text"]
                : "The response could not be generated.";
            // Surface the failure in the transcript without throwing — the
            // store renders whatever text is present when the stream ends.
            text = text || `_${detail}_`;
          }
        },
      });
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        text = text || "_The response could not be generated._";
      }
    }

    callbacks.onFinish(text, aborted);
    return { text, aborted };
  })();

  return {
    stop: () => {
      if (aborted) return;
      aborted = true;
      controller.abort();
    },
    done,
  };
}

/** Parses a Server-Sent Events byte stream into (event, data) pairs. */
async function consumeSse(
  body: ReadableStream<Uint8Array>,
  handlers: { onEvent: (event: string, data: Record<string, unknown>) => void },
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line.
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        dispatchFrame(frame, handlers.onEvent);
        separator = buffer.indexOf("\n\n");
      }
    }
    if (buffer.trim()) dispatchFrame(buffer, handlers.onEvent);
  } finally {
    reader.releaseLock();
  }
}

function dispatchFrame(
  frame: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
): void {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }

  if (dataLines.length === 0) return;
  try {
    const data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    onEvent(event, data);
  } catch {
    /* ignore malformed frame */
  }
}
