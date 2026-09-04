import { useCallback, useEffect, useRef, useState } from "react";

import {
  createConversation as createConversationRequest,
  deleteConversation as deleteConversationRequest,
  listConversations,
  optimisticTitle,
  persistConversations,
  setMessageFeedback,
  streamCompletion,
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
  loadConversations: () => Promise<void>;
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
  const streamRef = useRef<CompletionStream | null>(null);
  const conversationsRef = useRef<Conversation[]>([]);

  conversationsRef.current = conversations;

  const loadConversations = useCallback(async () => {
    setConversations(await listConversations());
  }, []);

  /* mock durability — real API persists inside each mutation endpoint */
  useEffect(() => {
    if (!hydrated) return;
    void persistConversations(
      conversations,
      settings.saveHistory && settings.chatHistoryEnabled,
    );
  }, [conversations, hydrated, settings.saveHistory, settings.chatHistoryEnabled]);

  const patch = useCallback(
    (id: string, apply: (conversation: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((item) => (item.id === id ? apply(item) : item)));
    },
    [],
  );

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
      void createConversationRequest({ id, model: model ?? settings.defaultModel });
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

      streamRef.current = streamCompletion(
        {
          conversationId,
          prompt,
          history,
          model,
          settings: { responseStyle: settings.responseStyle, tone: settings.tone },
        },
        {
          onDelta: (text) => {
            patch(conversationId, (conversation) => ({
              ...conversation,
              messages: conversation.messages.map((message) =>
                message.id === assistantId ? { ...message, content: text } : message,
              ),
            }));
          },
          onFinish: (text, aborted) => {
            streamRef.current = null;
            setStreaming(null);
            patch(conversationId, (conversation) => ({
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
      const title = isFirst
        ? optimisticTitle(clean || attachments?.[0]?.name || "New chat")
        : existing?.title;

      patch(conversationId, (conversation) => ({
        ...conversation,
        title: title ?? conversation.title,
        updatedAt: userMessage.createdAt,
        messages: [...conversation.messages, userMessage],
      }));
      if (isFirst && title) void updateConversation(conversationId, { title });

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
    loadConversations,
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
