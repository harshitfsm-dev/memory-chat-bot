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

export interface CreateConversationPayload {
  model: ModelId;
  /** Optional client-generated id so the UI can navigate optimistically. */
  id?: string;
  title?: string;
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
  prompt: string;
  history: ChatMessage[];
  model: ModelId;
  settings: CompletionSettings;
  attachments?: Attachment[];
}

export interface StreamCompletionCallbacks {
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
