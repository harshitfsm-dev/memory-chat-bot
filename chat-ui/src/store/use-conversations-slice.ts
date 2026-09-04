import { useCallback, useEffect, useRef, useState } from "react";

import {
  deleteConversation as deleteConversationRequest,
  listMessages,
  listThreads,
  messageToChatMessage,
  optimisticTitle,
  setMessageFeedback,
  streamCompletion,
  threadToConversation,
  updateConversation,
} from "@/api";
import type { CompletionStream } from "@/api/types";
import { createId } from "@/lib/id";
import type { Attachment, ChatMessage, Conversation, ModelId, Settings } from "@/lib/types";

export interface StreamState {
  conversationId: string;
  messageId: string;
}

export interface ConversationsSlice {
  conversations: Conversation[];
  streaming: StreamState | null;
  /** Thread ids whose transcript is currently being fetched. */
  loadingMessages: ReadonlySet<string>;
  /**
   * Set when a locally-created chat adopts its backend thread id, so the view
   * can swap the URL from the temporary id to the real one.
   */
  threadRemap: { from: string; to: string } | null;
  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  clearConversations: () => void;
  getConversation: (id: string) => Conversation | undefined;
  createConversation: (model?: ModelId) => string;
  renameConversation: (id: string, title: string) => void;
  deleteConversation: (id: string) => void;
  toggleArchive: (id: string) => void;
  setModel: (id: string, model: ModelId) => void;
  sendMessage: (conversationId: string, text: string, attachments?: Attachment[]) => void;
  regenerate: (conversationId: string) => void;
  stopStreaming: () => void;
  setFeedback: (conversationId: string, messageId: string, value: "up" | "down") => void;
}

/** Owns the conversation collection and the completion lifecycle. */
export function useConversationsSlice(hydrated: boolean, settings: Settings): ConversationsSlice {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [streaming, setStreaming] = useState<StreamState | null>(null);
  const [loadingMessages, setLoadingMessages] = useState<ReadonlySet<string>>(new Set());
  const [threadRemap, setThreadRemap] = useState<{ from: string; to: string } | null>(null);
  const streamRef = useRef<CompletionStream | null>(null);
  const conversationsRef = useRef<Conversation[]>([]);
  /** Thread ids whose transcript has already been fetched from the backend. */
  const loadedMessagesRef = useRef<Set<string>>(new Set());
  /** Ids known to exist on the backend (loaded threads + reconciled new chats). */
  const serverThreadsRef = useRef<Set<string>>(new Set());

  conversationsRef.current = conversations;

  const loadConversations = useCallback(async () => {
    try {
      const threads = await listThreads();
      setConversations(threads.map(threadToConversation));
      loadedMessagesRef.current = new Set();
      serverThreadsRef.current = new Set(threads.map((thread) => thread.id));
    } catch {
      // Hydration runs before auth is guaranteed; a signed-out load returns
      // 401. Fail soft to an empty list so the app still finishes hydrating —
      // the /auth redirect handles the signed-out case.
      setConversations([]);
    }
  }, []);

  /**
   * Lazily fetch a thread's transcript the first time it is opened. Threads
   * arrive from the list endpoint without messages, so this fills them in.
   *
   * No-ops when the transcript is already loaded, a fetch is in flight, or the
   * thread is mid-stream (a locally created chat has no server transcript yet
   * and we must not overwrite the streaming placeholder).
   */
  const loadMessages = useCallback(async (conversationId: string) => {
    if (loadedMessagesRef.current.has(conversationId)) return;
    if (streamRef.current) return;

    loadedMessagesRef.current.add(conversationId);
    setLoadingMessages((prev) => new Set(prev).add(conversationId));
    try {
      const messages = await listMessages(conversationId);
      setConversations((prev) =>
        prev.map((item) =>
          item.id === conversationId
            ? { ...item, messages: messages.map(messageToChatMessage) }
            : item,
        ),
      );
    } catch {
      // Allow a retry on the next open (e.g. transient network failure).
      loadedMessagesRef.current.delete(conversationId);
    } finally {
      setLoadingMessages((prev) => {
        const next = new Set(prev);
        next.delete(conversationId);
        return next;
      });
    }
  }, []);

  /** Drop all conversation state. Called on sign-out so the next user starts clean. */
  const clearConversations = useCallback(() => {
    streamRef.current?.stop();
    streamRef.current = null;
    loadedMessagesRef.current = new Set();
    serverThreadsRef.current = new Set();
    setStreaming(null);
    setLoadingMessages(new Set());
    setThreadRemap(null);
    setConversations([]);
  }, []);

  const patch = useCallback((id: string, apply: (conversation: Conversation) => Conversation) => {
    setConversations((prev) => prev.map((item) => (item.id === id ? apply(item) : item)));
  }, []);

  const getConversation = useCallback(
    (id: string) => conversations.find((item) => item.id === id),
    [conversations],
  );

  const createConversation = useCallback(
    (model?: ModelId) => {
      const id = createId();
      const stamp = new Date().toISOString();
      setConversations((prev) => [
        {
          id,
          title: "New chat",
          createdAt: stamp,
          updatedAt: stamp,
          model: model ?? settings.defaultModel,
          archived: false,
          messages: [],
        },
        ...prev,
      ]);
      // Locally created: its transcript lives in memory, so never try to fetch
      // one from the backend (the id isn't a server thread id yet). The backend
      // creates the real thread lazily on the first streamed message and hands
      // back its id via the stream's `meta` event.
      loadedMessagesRef.current.add(id);
      return id;
    },
    [settings.defaultModel],
  );

  const renameConversation = useCallback(
    (id: string, title: string) => {
      const clean = title.trim();
      if (!clean) return;
      patch(id, (conversation) => ({ ...conversation, title: clean }));
      void updateConversation(id, { title: clean });
    },
    [patch],
  );

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => prev.filter((item) => item.id !== id));
    void deleteConversationRequest(id);
  }, []);

  const toggleArchive = useCallback(
    (id: string) => {
      const next = !conversationsRef.current.find((item) => item.id === id)?.archived;
      patch(id, (conversation) => ({ ...conversation, archived: next }));
      void updateConversation(id, { archived: next });
    },
    [patch],
  );

  const setModel = useCallback(
    (id: string, model: ModelId) => {
      patch(id, (conversation) => ({ ...conversation, model }));
      void updateConversation(id, { model });
    },
    [patch],
  );

  const setFeedback = useCallback(
    (conversationId: string, messageId: string, value: "up" | "down") => {
      let next: "up" | "down" | null = value;
      patch(conversationId, (conversation) => ({
        ...conversation,
        messages: conversation.messages.map((message) => {
          if (message.id !== messageId) return message;
          next = message.feedback === value ? null : value;
          return { ...message, feedback: next };
        }),
      }));
      void setMessageFeedback({ conversationId, messageId, value: next });
    },
    [patch],
  );

  /* -------------------------------------------------------------- streaming */
  const runStream = useCallback(
    (conversationId: string, prompt: string, history: ChatMessage[]) => {
      const assistantId = createId();
      const placeholder: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        feedback: null,
      };
      patch(conversationId, (conversation) => ({
        ...conversation,
        updatedAt: placeholder.createdAt,
        messages: [...conversation.messages, placeholder],
      }));
      setStreaming({ conversationId, messageId: assistantId });

      const model =
        conversationsRef.current.find((item) => item.id === conversationId)?.model ??
        settings.defaultModel;

      // The id can change mid-stream: a brand-new local chat adopts the
      // backend thread id from the `meta` event. Track it so later patches and
      // the streaming marker follow the conversation across the rename.
      let activeId = conversationId;
      const threadId = serverThreadsRef.current.has(conversationId) ? conversationId : null;

      streamRef.current = streamCompletion(
        {
          conversationId,
          threadId,
          prompt,
          history,
          model,
          settings: { responseStyle: settings.responseStyle, tone: settings.tone },
        },
        {
          onMeta: (backendId, title) => {
            serverThreadsRef.current.add(backendId);
            if (backendId === activeId) {
              if (title) patch(activeId, (c) => ({ ...c, title }));
              return;
            }
            // Adopt the backend id in place of the temporary local id.
            const fromId = activeId;
            if (loadedMessagesRef.current.has(fromId)) {
              loadedMessagesRef.current.delete(fromId);
            }
            loadedMessagesRef.current.add(backendId);
            setConversations((prev) =>
              prev.map((c) =>
                c.id === fromId ? { ...c, id: backendId, title: title || c.title } : c,
              ),
            );
            setStreaming((prev) =>
              prev && prev.conversationId === fromId
                ? { ...prev, conversationId: backendId }
                : prev,
            );
            activeId = backendId;
            setThreadRemap({ from: fromId, to: backendId });
          },
          onDelta: (text) => {
            patch(activeId, (conversation) => ({
              ...conversation,
              messages: conversation.messages.map((message) =>
                message.id === assistantId ? { ...message, content: text } : message,
              ),
            }));
          },
          onFinish: (text, aborted) => {
            streamRef.current = null;
            setStreaming(null);
            patch(activeId, (conversation) => ({
              ...conversation,
              updatedAt: new Date().toISOString(),
              messages: conversation.messages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content:
                        text || (aborted ? "_Response stopped._" : "_No response generated._"),
                    }
                  : message,
              ),
            }));
          },
        },
      );
    },
    [patch, settings.defaultModel, settings.responseStyle, settings.tone],
  );

  const sendMessage = useCallback(
    (conversationId: string, text: string, attachments?: Attachment[]) => {
      const clean = text.trim();
      if (!clean && !attachments?.length) return;
      streamRef.current?.stop();

      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: clean,
        createdAt: new Date().toISOString(),
        ...(attachments && attachments.length > 0 ? { attachments } : {}),
      };

      const existing = conversationsRef.current.find((item) => item.id === conversationId);
      const history = existing?.messages ?? [];
      const isFirst = history.length === 0;
      // Optimistic local title until the backend returns the real one via meta.
      const title = isFirst
        ? optimisticTitle(clean || attachments?.[0]?.name || "New chat")
        : existing?.title;

      patch(conversationId, (conversation) => ({
        ...conversation,
        title: title ?? conversation.title,
        updatedAt: userMessage.createdAt,
        messages: [...conversation.messages, userMessage],
      }));

      runStream(conversationId, clean, history);
    },
    [patch, runStream],
  );

  const regenerate = useCallback(
    (conversationId: string) => {
      streamRef.current?.stop();
      const conversation = conversationsRef.current.find((item) => item.id === conversationId);
      if (!conversation) return;
      const messages = [...conversation.messages];
      while (messages.length > 0 && messages[messages.length - 1]!.role === "assistant")
        messages.pop();
      const lastUser = messages[messages.length - 1];
      if (!lastUser) return;
      patch(conversationId, (item) => ({ ...item, messages }));
      runStream(conversationId, lastUser.content, messages.slice(0, -1));
    },
    [patch, runStream],
  );

  const stopStreaming = useCallback(() => streamRef.current?.stop(), []);

  useEffect(() => () => streamRef.current?.stop(), []);

  return {
    conversations,
    streaming,
    loadingMessages,
    threadRemap,
    loadConversations,
    loadMessages,
    clearConversations,
    getConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    toggleArchive,
    setModel,
    sendMessage,
    regenerate,
    stopStreaming,
    setFeedback,
  };
}
