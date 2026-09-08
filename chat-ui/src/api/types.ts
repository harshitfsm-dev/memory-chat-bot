import type {
  Attachment,
  ChatMessage,
  Conversation,
  ModelId,
  ResponseStyle,
  Settings,
  Tone,
  UserProfile,
} from "@/lib/types";

/** Shape returned by the auth endpoints. */
export interface Session {
  signedIn: boolean;
  user: UserProfile;
}

/** Credentials sent to the backend login endpoint. */
export interface LoginPayload {
  email: string;
  password: string;
}

/** Token envelope returned by `POST /auth/login`. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export type ConversationPatch = Partial<Pick<Conversation, "title" | "archived" | "model">>;

export interface MessageFeedbackPayload {
  conversationId: string;
  messageId: string;
  value: "up" | "down" | null;
}

export interface CompletionSettings {
  responseStyle: ResponseStyle;
  tone: Tone;
}

export interface StreamCompletionPayload {
  conversationId: string;
  /**
   * Backend thread id to continue, or null to start a new thread. The backend
   * owns thread creation and returns the real id via the `meta` event.
   */
  threadId: string | null;
  prompt: string;
  history: ChatMessage[];
  model: ModelId;
  settings: CompletionSettings;
  attachments?: Attachment[];
}

export interface StreamCompletionCallbacks {
  /**
   * Fires once when the backend resolves the thread, before any tokens. For a
   * new chat this carries the server-generated thread id and title so the
   * client can adopt them.
   */
  onMeta?: (threadId: string, threadTitle: string) => void;
  onDelta: (fullText: string) => void;
  onFinish: (fullText: string, aborted: boolean) => void;
}

/** Handle to an in-flight completion — identical for mock and real transports. */
export interface CompletionStream {
  stop: () => void;
  done: Promise<{ text: string; aborted: boolean }>;
}

export interface UploadHandle {
  attachment: Attachment;
  cancel: () => void;
  done: Promise<Attachment>;
}

export type SettingsPayload = Settings;

/**
 * Raw thread record returned by `GET /chat/threads`.
 * Field names mirror the backend (snake_case) exactly.
 */
export interface ThreadResponse {
  id: string;
  title: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Raw message record returned by `GET /chat/messages`.
 * Field names mirror the backend (snake_case) exactly.
 */
export interface MessageResponse {
  id: string;
  thread_id: string;
  role: string;
  content: string;
  created_at: string;
}

/** Closed routing dimension for notes. Null for facts. */
export type MemoryCategory =
  "goal" | "plan" | "event" | "project" | "constraint" | "interest" | "other";

/** User-visible long-term memory returned by the backend management API. */
export interface MemoryItemResponse {
  id: string;
  /** Set on facts only: which profile field this is. */
  memory_key: string | null;
  /** Set on notes only. */
  category: MemoryCategory | null;
  /** Set on notes only: a few words naming the topic. */
  subject: string | null;
  content: string;
  /**
   * Present on the response for compatibility but unused: notes do not carry an
   * event date or expiry in this build.
   */
  event_at: string | null;
  valid_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserMemoriesResponse {
  /** Pinned profile facts (name, occupation, preferences, ...). */
  facts: MemoryItemResponse[];
  /**
   * Free-text memories in the user's own words, retrieved by relevance. Reviewing
   * this group is how a user catches something that should not have been stored.
   */
  notes: MemoryItemResponse[];
}
