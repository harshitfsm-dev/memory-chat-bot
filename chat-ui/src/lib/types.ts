export type Role = "user" | "assistant";

export type AttachmentStatus = "uploading" | "done" | "error";

export interface Attachment {
  id: string;
  name: string;
  /** mime type, e.g. application/pdf */
  mime: string;
  /** size in bytes */
  size: number;
  status: AttachmentStatus;
  /** 0 - 100 */
  progress: number;
  /** local object URL for images only */
  previewUrl?: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  attachments?: Attachment[];
  feedback?: "up" | "down" | null;
}

export type ModelId =
  | "auto"
  | "llama3.1:8b"
  | "llama3.2:3b"
  | "deepseek-r1:14b"
  | "qwen3.6:27b-mlx"
  | "gemma4:e4b-mlx"
  | "qwen3.5:2b-mlx"
  | "gemma4:12b-mlx";

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  model: ModelId;
  archived: boolean;
  pinnedIcon?: string;
  messages: ChatMessage[];
}

export interface UserProfile {
  name: string;
  email: string;
  initials: string;
  plan: string;
}

export type ThemeMode = "light" | "dark" | "system";
export type ResponseStyle = "concise" | "balanced" | "detailed" | "custom";
export type Tone = "professional" | "friendly" | "casual" | "technical";

export interface Settings {
  // General
  theme: ThemeMode;
  language: string;
  compactMode: boolean;
  animations: boolean;
  // AI preferences
  aboutAi: string;
  responseGuidance: string;
  responseStyle: ResponseStyle;
  tone: Tone;
  // Personalization
  aboutMe: string;
  myPreferences: string;
  instructions: string;
  // Chat
  enterToSend: boolean;
  showTimestamps: boolean;
  autoScroll: boolean;
  saveHistory: boolean;
  defaultModel: ModelId;
  // Privacy
  chatHistoryEnabled: boolean;
  improveAi: boolean;
  rememberPreferences: boolean;
}

export interface Model {
  id: ModelId;
  name: string;
  description: string;
}

export const MODELS: Model[] = [
  { id: "auto", name: "Auto", description: "Automatically pick the best model for each message" },
  { id: "llama3.1:8b", name: "Llama 3.1 8B", description: "Balanced general-purpose model" },
  { id: "llama3.2:3b", name: "Llama 3.2 3B", description: "Fast, lightweight responses" },
  { id: "deepseek-r1:14b", name: "DeepSeek R1 14B", description: "Deeper reasoning and analysis" },
  { id: "qwen3.6:27b-mlx", name: "Qwen 3.6 27B", description: "Largest model, most capable" },
  { id: "gemma4:e4b-mlx", name: "Gemma 4 E4B", description: "Efficient on-device model" },
  { id: "qwen3.5:2b-mlx", name: "Qwen 3.5 2B", description: "Compact and quick" },
  { id: "gemma4:12b-mlx", name: "Gemma 4 12B", description: "Strong reasoning at mid size" },
];
