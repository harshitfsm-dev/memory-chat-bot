import { useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ChatComposer } from "@/components/nova/chat-composer";
import { ChatHeader } from "@/components/nova/chat-header";
import { ChatEmptyState } from "@/components/nova/chat/chat-empty-state";
import { ChatNavigation } from "@/components/nova/chat/chat-navigation";
import { ChatSkeleton } from "@/components/nova/chat/chat-skeleton";
import { ChatTranscript } from "@/components/nova/chat/chat-transcript";
import { ChatTranscriptSkeleton } from "@/components/nova/chat/chat-transcript-skeleton";
import { RenameConversationDialog } from "@/components/nova/chat/rename-conversation-dialog";
import { ConfirmDialog } from "@/components/nova/confirm-dialog";
import { SettingsDialog } from "@/components/nova/settings-dialog";
import { useAttachmentUploads } from "@/hooks/use-attachment-uploads";
import { useChatShortcuts } from "@/hooks/use-chat-shortcuts";
import type { Conversation as Chat, ModelId } from "@/lib/types";
import { useApp } from "@/store/app-store";

export function ChatView({ chatId }: { chatId: string | null }) {
  const navigate = useNavigate();
  const {
    hydrated,
    auth,
    signOut,
    settings,
    saveSettings,
    updateSettings,
    resolvedTheme,
    conversations,
    getConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    toggleArchive,
    setModel,
    sendMessage,
    regenerate,
    stopStreaming,
    streaming,
    setFeedback,
    loadMessages,
    loadingMessages,
  } = useApp();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [renameTarget, setRenameTarget] = useState<Chat | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null);
  const [clearAllOpen, setClearAllOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);

  const { attachments, addFiles, removeAttachment, clearAttachments } = useAttachmentUploads();

  const conversation = chatId ? (getConversation(chatId) ?? null) : null;
  const model: ModelId = conversation?.model ?? settings.defaultModel;
  const isStreaming = Boolean(conversation && streaming?.conversationId === conversation.id);
  const messages = conversation?.messages ?? [];
  const isLoadingMessages = Boolean(chatId && loadingMessages.has(chatId));

  /* ------------------------------------------------------------ redirects */
  useEffect(() => {
    if (hydrated && !auth.signedIn) navigate({ to: "/auth", replace: true });
  }, [hydrated, auth.signedIn, navigate]);

  useEffect(() => {
    if (hydrated && chatId && !conversation) navigate({ to: "/", replace: true });
  }, [hydrated, chatId, conversation, navigate]);

  /* Lazily load the transcript the first time a thread is opened. */
  useEffect(() => {
    if (hydrated && chatId && conversation) void loadMessages(chatId);
  }, [hydrated, chatId, conversation, loadMessages]);

  useEffect(() => {
    setDraft("");
    clearAttachments();
  }, [chatId, clearAttachments]);

  const handleNewChat = useCallback(() => {
    setMobileOpen(false);
    void navigate({ to: "/" });
  }, [navigate]);

  useChatShortcuts({
    onSearch: () => {
      setCollapsed(false);
      setMobileOpen(true);
      window.setTimeout(() => searchRef.current?.focus(), 60);
    },
    onNewChat: handleNewChat,
    onToggleSidebar: () => setCollapsed((prev) => !prev),
  });

  /* ----------------------------------------------------------------- send */
  const submit = useCallback(
    (overrideText?: string) => {
      const text = (overrideText ?? draft).trim();
      if (!text && attachments.length === 0) return;
      const targetId = conversation?.id ?? createConversation(model);
      if (!conversation) void navigate({ to: "/c/$chatId", params: { chatId: targetId } });
      sendMessage(targetId, text, attachments.length > 0 ? attachments : undefined);
      setDraft("");
      clearAttachments();
    },
    [
      attachments,
      clearAttachments,
      conversation,
      createConversation,
      draft,
      model,
      navigate,
      sendMessage,
    ],
  );

  const handleModelChange = useCallback(
    (next: ModelId) => {
      if (conversation) setModel(conversation.id, next);
      else updateSettings({ defaultModel: next });
    },
    [conversation, setModel, updateSettings],
  );

  const handleArchive = useCallback(
    (item: Chat) => {
      toggleArchive(item.id);
      toast.success(item.archived ? "Conversation restored" : "Conversation archived");
    },
    [toggleArchive],
  );

  if (!hydrated) return <ChatSkeleton />;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <ChatNavigation
        conversations={conversations}
        activeId={conversation?.id ?? null}
        user={auth.user}
        theme={resolvedTheme}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        searchRef={searchRef}
        onMobileOpenChange={setMobileOpen}
        onCollapse={() => setCollapsed(true)}
        onExpand={() => setCollapsed(false)}
        onNewChat={handleNewChat}
        onRename={setRenameTarget}
        onDelete={setDeleteTarget}
        onArchive={handleArchive}
        onOpenSettings={() => setSettingsOpen(true)}
        onToggleTheme={() => updateSettings({ theme: resolvedTheme === "dark" ? "light" : "dark" })}
        onSignOut={() => {
          signOut();
          void navigate({ to: "/auth", replace: true });
        }}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          conversation={conversation}
          model={model}
          onToggleSidebar={() => {
            setMobileOpen(true);
            setCollapsed((prev) => !prev);
          }}
          onRename={() => conversation && setRenameTarget(conversation)}
          onDelete={() => conversation && setDeleteTarget(conversation)}
          onArchive={() => conversation && handleArchive(conversation)}
          onModelChange={handleModelChange}
        />

        {messages.length === 0 && isLoadingMessages ? (
          <ChatTranscriptSkeleton />
        ) : messages.length === 0 ? (
          <ChatEmptyState userName={auth.user.name} onSelectPrompt={(prompt) => submit(prompt)} />
        ) : (
          <ChatTranscript
            messages={messages}
            streamingMessageId={isStreaming ? (streaming?.messageId ?? null) : null}
            showTimestamps={settings.showTimestamps}
            compact={settings.compactMode}
            userInitials={auth.user.initials}
            onRegenerate={() => conversation && regenerate(conversation.id)}
            onFeedback={(messageId, value) =>
              conversation && setFeedback(conversation.id, messageId, value)
            }
          />
        )}

        <div className="border-t bg-background/80 px-3 py-3 backdrop-blur-md sm:px-4">
          <ChatComposer
            value={draft}
            onValueChange={setDraft}
            attachments={attachments}
            onAddFiles={addFiles}
            onRemoveAttachment={removeAttachment}
            onSubmit={() => submit()}
            onStop={stopStreaming}
            isStreaming={isStreaming}
            model={model}
            onModelChange={handleModelChange}
            enterToSend={settings.enterToSend}
            autoFocusKey={chatId ?? "new"}
          />
        </div>
      </main>

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        settings={settings}
        onSave={saveSettings}
        onClearAll={() => setClearAllOpen(true)}
      />

      <RenameConversationDialog
        conversation={renameTarget}
        onOpenChange={(open) => !open && setRenameTarget(null)}
        onRename={renameConversation}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete conversation?"
        description={`“${deleteTarget?.title ?? ""}” will be removed from this browser.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (!deleteTarget) return;
          const wasActive = deleteTarget.id === conversation?.id;
          deleteConversation(deleteTarget.id);
          setDeleteTarget(null);
          toast.success("Conversation deleted");
          if (wasActive) void navigate({ to: "/" });
        }}
      />

      <ConfirmDialog
        open={clearAllOpen}
        onOpenChange={setClearAllOpen}
        title="Delete all chats?"
        description="Every conversation stored in this browser will be removed."
        confirmLabel="Delete all"
        destructive
        onConfirm={() => {
          conversations.forEach((item) => deleteConversation(item.id));
          setClearAllOpen(false);
          toast.success("All chats deleted");
          void navigate({ to: "/" });
        }}
      />
    </div>
  );
}
