import { MOCK_REPLIES } from "./mock-data";
import type { ChatMessage, Settings } from "@/lib/types";

/**
 * Mock streaming layer.
 *
 * This is the single seam between the UI and "the model". To connect a real
 * backend later, replace `streamMockCompletion` with a function that reads
 * from a fetch/SSE stream and calls the same callbacks.
 */

export interface StreamHandle {
  /** Abort the in-flight completion. */
  stop: () => void;
  /** Resolves when the stream finishes or is aborted. */
  done: Promise<{ text: string; aborted: boolean }>;
}

export interface StreamRequest {
  prompt: string;
  history: ChatMessage[];
  settings: Pick<Settings, "responseStyle" | "tone">;
  onDelta: (fullText: string) => void;
  onFinish?: (fullText: string, aborted: boolean) => void;
}

function pickReply(prompt: string): string {
  const p = prompt.toLowerCase();
  if (/hello|hi\b|hey/.test(p)) {
    return `Hey — good to see you. What are we working on?\n\nI can help you draft something, dig through a file, or reason through a decision. Just describe the messy version and I'll shape it.`;
  }
  if (/code|bug|error|typescript|python|react/.test(p)) return MOCK_REPLIES[2]!;
  if (/write|draft|copy|tagline|headline/.test(p)) return MOCK_REPLIES[3]!;
  if (/compare|option|versus|vs\b|should i/.test(p)) return MOCK_REPLIES[1]!;
  if (/analy|data|report|numbers|csv/.test(p)) return MOCK_REPLIES[4]!;
  const index = Math.abs(hash(prompt)) % MOCK_REPLIES.length;
  return MOCK_REPLIES[index]!;
}

function hash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) h = (h << 5) - h + value.charCodeAt(i);
  return h;
}

function styleWrap(text: string, style: StreamRequest["settings"]["responseStyle"]): string {
  if (style === "concise") return text.split("\n\n").slice(0, 2).join("\n\n");
  if (style === "detailed")
    return `${text}\n\n---\n\nA bit more context: this holds for the common case, and the exceptions usually involve scale or a hard deadline. If either applies, tell me and I'll adjust the recommendation.`;
  return text;
}

/** Splits text into stream-sized chunks (words, keeping whitespace). */
function chunk(text: string): string[] {
  return text.match(/\s*\S+/g) ?? [];
}

export function streamMockCompletion(request: StreamRequest): StreamHandle {
  const full = styleWrap(pickReply(request.prompt), request.settings.responseStyle);
  const parts = chunk(full);

  let aborted = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let resolveDone: (value: { text: string; aborted: boolean }) => void;
  const done = new Promise<{ text: string; aborted: boolean }>((resolve) => {
    resolveDone = resolve;
  });

  let text = "";
  let i = 0;

  const finish = () => {
    request.onFinish?.(text, aborted);
    resolveDone({ text, aborted });
  };

  const tick = () => {
    if (aborted) return;
    if (i >= parts.length) {
      finish();
      return;
    }
    // emit 1-3 words per tick for a natural cadence
    const burst = 1 + Math.floor(Math.random() * 3);
    text += parts.slice(i, i + burst).join("");
    i += burst;
    request.onDelta(text);
    timer = setTimeout(tick, 18 + Math.random() * 45);
  };

  // small "thinking" latency before the first token
  timer = setTimeout(tick, 550 + Math.random() * 450);

  return {
    stop: () => {
      if (aborted) return;
      aborted = true;
      if (timer) clearTimeout(timer);
      finish();
    },
    done,
  };
}

/** Mock title generation from the first user message. */
export function deriveTitle(prompt: string): string {
  const clean = prompt.replace(/\s+/g, " ").trim();
  if (!clean) return "New chat";
  const words = clean.split(" ").slice(0, 6).join(" ");
  const title = words.charAt(0).toUpperCase() + words.slice(1);
  return title.length < clean.length ? `${title}…` : title;
}
