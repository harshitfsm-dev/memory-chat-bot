/**
 * API surface consumed by the app.
 *
 * Components and stores import from here only — every endpoint lives in its own
 * file and currently resolves mock data. Swapping to the real backend means
 * editing those endpoint files, nothing else.
 */
export { getSession } from "./auth/get-session";
export { login } from "./auth/login";
export { signOut } from "./auth/sign-out";

export { getSettings } from "./settings/get-settings";
export { saveSettings } from "./settings/save-settings";

export { updateConversation } from "./conversations/update-conversation";
export { deleteConversation } from "./conversations/delete-conversation";

export { streamCompletion } from "./messages/stream-completion";
export { optimisticTitle } from "./messages/generate-title";
export { setMessageFeedback } from "./messages/set-message-feedback";

export { uploadAttachment, MAX_UPLOAD_SIZE } from "./files/upload-attachment";

export { listThreads, threadToConversation } from "./threads/list-threads";
export { listMessages, messageToChatMessage } from "./threads/list-messages";

export { ApiError } from "./http";
export type * from "./types";
