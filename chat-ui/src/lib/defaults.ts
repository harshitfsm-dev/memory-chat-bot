import type { Settings, UserProfile } from "./types";

/** Baseline settings used before the settings endpoint resolves. */
export const DEFAULT_SETTINGS: Settings = {
  theme: "system",
  language: "en-US",
  compactMode: false,
  animations: true,
  aboutAi:
    "I lead product marketing at a B2B SaaS company. I work mostly with analytics, launch plans and positioning docs.",
  responseGuidance:
    "Lead with the answer, then supporting detail. Use short paragraphs and bullet lists. Skip disclaimers.",
  responseStyle: "balanced",
  tone: "professional",
  aboutMe: "Based in Bengaluru. Prefers metric units and ISO dates.",
  myPreferences: "Markdown formatting, tables for comparisons, code in TypeScript when relevant.",
  instructions: "Ask one clarifying question when a request is ambiguous, then proceed.",
  enterToSend: true,
  showTimestamps: true,
  autoScroll: true,
  saveHistory: true,
  defaultModel: "nova-fast",
  chatHistoryEnabled: true,
  improveAi: false,
  rememberPreferences: true,
};

/** Placeholder profile shown while the session endpoint resolves. */
export const GUEST_USER: UserProfile = {
  name: "Nova User",
  email: "you@novalabs.io",
  initials: "NU",
  plan: "Nova Plus",
};
